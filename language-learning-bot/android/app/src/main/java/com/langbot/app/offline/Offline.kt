package com.langbot.app.offline

import android.content.Context
import com.google.gson.Gson
import com.langbot.app.network.BLSClient
import com.langbot.app.network.BundleWord
import com.langbot.app.network.Card
import com.langbot.app.network.ResultEvent
import com.langbot.app.network.ResultsBatchRequest
import java.io.File
import java.util.UUID

/** A prefetched session bundle persisted on disk, plus the local study cursor. */
data class StoredBundle(
    val userId: String,
    val languageId: String,
    val words: List<BundleWord>,
    val cursor: Int = 0,
)

/** One accumulated, not-yet-synced study result. */
data class OutboxEntry(
    val userId: String,
    val languageId: String,
    val event_id: String,
    val word_id: String,
    val rating: String,   // know | dont_know | skip
    val ts: String,
)

/**
 * File-based offline cache: the prefetched bundle (per user+language) and a global
 * outbox of unsent results. Simple, dependency-free (Gson + filesDir), thread-safe.
 */
object OfflineCache {
    private lateinit var appCtx: Context
    private val gson = Gson()
    private val lock = Any()

    fun init(ctx: Context) { appCtx = ctx.applicationContext }
    private fun ready() = ::appCtx.isInitialized

    private fun bundleFile(u: String, l: String) = File(appCtx.filesDir, "bundle_${u}_${l}.json")
    private val outboxFile get() = File(appCtx.filesDir, "outbox.json")

    // ── Bundle ──
    fun saveBundle(b: StoredBundle) {
        synchronized(lock) {
            if (!ready()) return
            runCatching { bundleFile(b.userId, b.languageId).writeText(gson.toJson(b)) }
        }
    }

    fun loadBundle(u: String, l: String): StoredBundle? = synchronized(lock) {
        if (!ready()) return null
        val f = bundleFile(u, l)
        if (!f.exists()) return null
        return runCatching { gson.fromJson(f.readText(), StoredBundle::class.java) }.getOrNull()
    }

    fun saveCursor(u: String, l: String, cursor: Int) = synchronized(lock) {
        loadBundle(u, l)?.let { saveBundle(it.copy(cursor = cursor)) }
    }

    // ── Outbox ──
    fun addResult(u: String, l: String, wordId: String, rating: String) = synchronized(lock) {
        if (!ready()) return
        val list = loadOutbox().toMutableList()
        list.add(OutboxEntry(u, l, UUID.randomUUID().toString(), wordId, rating, nowTs()))
        writeOutbox(list)
    }

    fun loadOutbox(): List<OutboxEntry> = synchronized(lock) {
        if (!ready()) return emptyList()
        val f = outboxFile
        if (!f.exists()) return emptyList()
        return runCatching { gson.fromJson(f.readText(), Array<OutboxEntry>::class.java).toList() }
            .getOrDefault(emptyList())
    }

    fun removeEvents(ids: Set<String>) = synchronized(lock) {
        writeOutbox(loadOutbox().filter { it.event_id !in ids })
    }

    private fun writeOutbox(list: List<OutboxEntry>) {
        runCatching { outboxFile.writeText(gson.toJson(list)) }
    }

    fun pendingCount(): Int = loadOutbox().size

    /** Zero-padded epoch millis → lexicographic order == chronological order. */
    private fun nowTs(): String = tsOf(System.currentTimeMillis())

    /** Pure formatter for a timestamp (extracted for unit testing). */
    fun tsOf(millis: Long): String = String.format("%020d", millis)
}

/**
 * Flushes the outbox to BLS /results/batch, grouped by (user, language).
 * Acked events are removed. Safe to call repeatedly; no-op when empty/offline.
 */
object OutboxSync {
    suspend fun flush() {
        val all = OfflineCache.loadOutbox()
        if (all.isEmpty()) return
        val acked = mutableSetOf<String>()
        all.groupBy { it.userId to it.languageId }.forEach { (key, entries) ->
            val (uid, lid) = key
            val req = ResultsBatchRequest(
                user_id = uid, language_id = lid,
                events = entries.map { ResultEvent(it.event_id, it.word_id, it.rating, it.ts) },
            )
            try {
                val resp = BLSClient.api.postResultsBatch(req)
                if (resp.isSuccessful) {
                    resp.body()?.acks
                        ?.filter { it.status == "ok" || it.status == "duplicate" }
                        ?.forEach { acked.add(it.event_id) }
                }
            } catch (_: Exception) { /* offline — keep for next flush */ }
        }
        if (acked.isNotEmpty()) OfflineCache.removeEvents(acked)
    }
}

/**
 * Local study engine backed by a prefetched bundle. Serves cards from cache and
 * records results into the outbox — no network needed.
 */
class OfflineEngine(private val bundle: StoredBundle) {
    val userId get() = bundle.userId
    val languageId get() = bundle.languageId
    private val words = bundle.words
    var cursor = bundle.cursor
        private set

    /**
     * Встать на слово [wordId]; пустой id означает «где стояли, там и стоим».
     *
     * @return false, если такого слова в офлайн-партии нет. Курсор тогда не
     * двигается, и вызывающий обязан знать: на экране было одно слово, а движок
     * стоит на другом — записывать за него оценку нельзя.
     */
    fun positionAtWord(wordId: String?): Boolean {
        if (wordId.isNullOrEmpty()) return true
        val i = words.indexOfFirst { it.word_id == wordId }
        if (i < 0) return false
        cursor = i
        return true
    }

    fun hasCurrent(): Boolean = cursor in words.indices
    fun frontCard(): Card? = words.getOrNull(cursor)?.card_front
    fun answerCard(): Card? = words.getOrNull(cursor)?.card_answer
    fun currentWordId(): String? = words.getOrNull(cursor)?.word_id
    fun atEnd(): Boolean = cursor >= words.size

    /** Record a result for the current word into the outbox. */
    fun record(rating: String) {
        val wid = currentWordId() ?: return
        OfflineCache.addResult(userId, languageId, wid, rating)
    }

    fun advance() {
        cursor++
        OfflineCache.saveCursor(userId, languageId, cursor)
    }

    companion object {
        fun fromStore(u: String, l: String): OfflineEngine? =
            OfflineCache.loadBundle(u, l)?.let { OfflineEngine(it) }
    }
}
