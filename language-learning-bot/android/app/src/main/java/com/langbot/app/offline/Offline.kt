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
    // Слова, отвеченные до перезапуска сессии: в новый круг они не входят.
    // Онлайн сервер пересчитывает набор на день и уже отвеченное не выдаёт;
    // офлайн партия скачана целиком, и без этого списка «начать заново»
    // показывало их по второму разу, а счётчик оставался прежним.
    //
    // Тип обнуляемый намеренно: Gson обходит умолчания Kotlin, когда не у всех
    // полей есть значения по умолчанию, и в партиях, сохранённых до этой
    // версии, здесь оказался бы null вопреки типу.
    val excluded: Set<String>? = null,
    // Настройки на момент скачивания партии. Сервер присылал их всегда, а
    // телефон выбрасывал — и экран настроек без сети оставался пустым, хотя
    // показать было что. Менять их без сети всё равно нельзя: состав слов
    // пересчитывает сервер. Тип обнуляемый по той же причине, что и excluded.
    val settings: Map<String, Any>? = null,
    // Сколько слов просили у сервера и когда — по ним решается, нужно ли
    // качать партию заново. См. BundleRefresh.
    val requestedSize: Int? = null,
    val savedAt: Long? = null,
)

/**
 * Нужно ли качать офлайн-партию заново.
 *
 * Прежде она перекачивалась при каждом открытии экрана занятия. Пока партия
 * была ровно на сто слов, это стоило около полутора мегабайт; с настройкой
 * размера человек может попросить и пятьсот — тогда на каждый вход уходило бы
 * под восемь мегабайт трафика и несколько секунд работы сервера.
 *
 * Свежее от этого партия всё равно не становится: она устаревает от ответов,
 * которые человек даёт ПОСЛЕ скачивания, а не от времени. Поэтому достаточно
 * качать её заново, когда партия кончается, когда изменили размер — и не чаще
 * раза в полчаса в остальных случаях.
 */
object BundleRefresh {
    const val MAX_AGE_MS = 30 * 60 * 1000L

    /** Докуда партию можно не трогать: пока пройдено меньше трёх четвертей. */
    private const val KEEP_WHILE_LEFT = 4

    fun needed(stored: StoredBundle?, wantedSize: Int, now: Long): Boolean {
        if (stored == null || stored.words.isEmpty()) return true
        // Размер поменяли — партия обязана стать такой, как просили.
        if ((stored.requestedSize ?: stored.words.size) != wantedSize) return true
        val left = stored.words.size - stored.cursor
        if (left * KEEP_WHILE_LEFT < stored.words.size) return true
        val savedAt = stored.savedAt ?: return true   // партия из старой версии
        if (now < savedAt) return true                // часы съехали назад
        return now - savedAt >= MAX_AGE_MS
    }
}

/**
 * Сколько пройдено к этому моменту — по последней карточке, пришедшей из сети.
 *
 * Нужно, когда экран слова открывают заново уже без связи: сервер молчит, свои
 * ответы в очереди пусты (прошлые уже отправлены), и счётчики показывали ноль,
 * хотя человек прошёл сегодня несколько слов. Храним с датой: в новый день
 * сервер считает заново, и старый отсчёт врал бы.
 */
data class SavedProgress(
    val correct: Int = 0,
    val wrong: Int = 0,
    val history: List<String> = emptyList(),
    val day: String = "",
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
            dayRule = null   // в новой партии граница суток могла измениться
            runCatching { bundleFile(b.userId, b.languageId).writeText(gson.toJson(b)) }
        }
    }

    fun loadBundle(u: String, l: String): StoredBundle? = synchronized(lock) {
        if (!ready()) return null
        val f = bundleFile(u, l)
        if (!f.exists()) return null
        return runCatching { gson.fromJson(f.readText(), StoredBundle::class.java) }.getOrNull()
    }

    /**
     * Перезапуск круга: из партии выводится то, что человек ЗНАЕТ.
     *
     * Онлайн «начать заново» отдаёт только оставшиеся на сегодня слова, и
     * правило у сервера такое: ответ «не знаю» ставит счёт 0 и стирает дату
     * следующей проверки — слово остаётся в обороте и выдаётся снова. Офлайн
     * партия скачана целиком и о прошедших ответах знает только из outbox.
     *
     * Сначала здесь выводились все отвеченные подряд, независимо от оценки. В
     * метро это незаметно: связь возвращается, ответы уходят, outbox пустеет,
     * и перезапуск не выводит ничего. А вот в самолёте, где связи нет вовсе,
     * пройденная партия объявлялась законченной — хотя половину слов человек
     * не знает, и именно их и надо было повторить.
     */
    fun excludeAnswered(u: String, l: String) = synchronized(lock) {
        val known = loadOutbox()
            .filter { it.userId == u && it.languageId == l && it.rating != "dont_know" }
            .map { it.word_id }.toSet()
        loadBundle(u, l)?.let { saveBundle(it.copy(cursor = 0, excluded = known)) }
    }

    private fun progressFile(u: String, l: String) =
        File(appCtx.filesDir, "progress_${u}_${l}.json")

    // Граница учебных суток: пояс и час берутся из настроек, доехавших в
    // партии. Разбирать партию на каждый показ карточки дорого — она на сотню
    // слов, — поэтому правило запоминается до смены партии.
    private var dayRule: Triple<String, String, Int>? = null

    /**
     * Какие сейчас учебные сутки — по правилу человека, а не устройства.
     *
     * Прежде здесь была местная полночь телефона, и она расходилась с
     * сервером: при начале суток в 4 утра занятие в полпервого ночи без сети
     * обнуляло счётчик пройденного, хотя сервер считал это продолжением
     * вчерашнего дня. Границ в системе было четыре; теперь одна — см.
     * common/study_day.py на сервере, тут её кусок для офлайна.
     */
    fun studyToday(u: String, l: String, nowMillis: Long = System.currentTimeMillis()): String {
        val key = "$u/$l"
        val rule = dayRule?.takeIf { it.first == key } ?: run {
            val s = loadBundle(u, l)?.settings
            val tz = (s?.get("timezone") as? String)?.takeIf { it.isNotBlank() } ?: "UTC"
            val hour = ((s?.get("day_start_hour") as? Number)?.toInt() ?: 0).coerceIn(0, 23)
            Triple(key, tz, hour).also { dayRule = it }
        }
        return StudyDay.of(nowMillis, rule.second, rule.third)
    }

    fun saveProgress(u: String, l: String, correct: Int, wrong: Int, history: List<String>) {
        synchronized(lock) {
            if (!ready()) return
            runCatching {
                progressFile(u, l).writeText(
                    gson.toJson(SavedProgress(correct, wrong, history, studyToday(u, l))))
            }
        }
    }

    /** Отсчёт этого дня; из прошлого дня не возвращаем — он уже неверен. */
    fun loadProgress(u: String, l: String): SavedProgress? = synchronized(lock) {
        if (!ready()) return null
        val f = progressFile(u, l)
        if (!f.exists()) return null
        val p = runCatching { gson.fromJson(f.readText(), SavedProgress::class.java) }.getOrNull()
        return if (p != null && p.day == studyToday(u, l)) p else null
    }

    fun clearProgress(u: String, l: String) = synchronized(lock) {
        runCatching { progressFile(u, l).delete() }
        Unit
    }

    fun saveCursor(u: String, l: String, cursor: Int) = synchronized(lock) {
        loadBundle(u, l)?.let { saveBundle(it.copy(cursor = cursor)) }
    }

    /**
     * Отметить в офлайн-партии слово, на котором человек стоит ОНЛАЙН.
     *
     * Курсор партии двигали только офлайновые ответы, а онлайновые — нет. Пока
     * связь есть, это незаметно; но стоит открыть экран без сети — и
     * приложение садится на то место, где курсор застыл в прошлый раз. С
     * экрана это выглядит как перескок на чужое слово: человек вчера дошёл до
     * двухсотого, а сегодня видит стодвадцатое.
     *
     * Слова нет в партии — ничего не делаем: место останется прежним, и это
     * честнее, чем встать наугад.
     */
    fun rememberPlace(u: String, l: String, wordId: String) = synchronized(lock) {
        if (wordId.isEmpty()) return
        val bundle = loadBundle(u, l) ?: return
        // Отсчёт — по тому же списку, по которому ходит движок: выведенные
        // прошлым кругом слова в него не входят, и индексы иначе разъедутся.
        val excluded = bundle.excluded ?: emptySet()
        val i = bundle.words.filter { it.word_id !in excluded }
            .indexOfFirst { it.word_id == wordId }
        if (i >= 0 && i != bundle.cursor) saveBundle(bundle.copy(cursor = i))
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
    // Слова круга: отвеченные до перезапуска в него не входят, иначе «начать
    // заново» показывало бы их снова.
    private val words = bundle.words.filter { it.word_id !in (bundle.excluded ?: emptySet()) }

    /** Сколько слов в этом круге — без выведенных перезапуском. */
    val total: Int get() = words.size

    /** Отвечено ли слово в прошлом круге. */
    fun isExcluded(wordId: String): Boolean = wordId in (bundle.excluded ?: emptySet())
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

    /** Ответ после «Знаю». В старых партиях его нет — тогда обычная ответная. */
    fun knownCard(): Card? = words.getOrNull(cursor)?.let { it.card_known ?: it.card_answer }
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
