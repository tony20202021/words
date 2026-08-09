package com.langbot.app.offline

import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File

/**
 * Tests for the parts of the offline layer that need a real `filesDir`.
 * Robolectric provides an Android Context on the JVM — no emulator involved.
 */
@RunWith(RobolectricTestRunner::class)
class OfflineCacheRobolectricTest {

    private val u = "user-1"
    private val l = "lang-1"

    private fun meta(pos: Int) = com.langbot.app.network.CardMeta(
        word_number = pos,
        session_pos = pos,
        session_total = 3,
        correct_count = 0,
        incorrect_count = 0,
        pending_result = null,
        score_badge = null,
    )

    private fun card(showAnswer: Boolean, pos: Int = 1) = com.langbot.app.network.Card(
        show_answer = showAnswer,
        content = emptyList(),
        buttons = emptyList(),
        meta = meta(pos),
    )

    private fun word(id: String, number: Int, sounds: List<String> = emptyList()) =
        com.langbot.app.network.BundleWord(
            word_id = id,
            word_number = number,
            card_front = card(false, number),
            card_answer = card(true, number),
            sounds = sounds,
        )

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        AudioCache.init(ctx)
        // Each test starts from a clean slate.
        File(ctx.filesDir, "sounds").deleteRecursively()
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
    }

    // ── bundle round-trip ────────────────────────────────────────────────────

    @Test
    fun saveBundle_then_loadBundle_returns_same_words() {
        val bundle = StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2)), cursor = 0)
        OfflineCache.saveBundle(bundle)

        val loaded = OfflineCache.loadBundle(u, l)
        assertNotNull(loaded)
        assertEquals(2, loaded!!.words.size)
        assertEquals("w1", loaded.words[0].word_id)
        assertEquals(2, loaded.words[1].word_number)
        assertEquals(false, loaded.words[0].card_front.show_answer)
        assertEquals(true, loaded.words[0].card_answer.show_answer)
    }

    @Test
    fun loadBundle_returns_null_for_a_different_user_or_language() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1))))
        assertNull(OfflineCache.loadBundle("other-user", l))
        assertNull(OfflineCache.loadBundle(u, "other-lang"))
    }

    @Test
    fun saveCursor_survives_reload() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2)), cursor = 0))
        OfflineCache.saveCursor(u, l, 1)
        assertEquals(1, OfflineCache.loadBundle(u, l)!!.cursor)
    }

    // ── outbox ───────────────────────────────────────────────────────────────

    @Test
    fun addResult_appends_to_outbox_and_pendingCount_tracks_it() {
        assertEquals(0, OfflineCache.pendingCount())
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.addResult(u, l, "w2", "dont_know")
        assertEquals(2, OfflineCache.pendingCount())

        val entries = OfflineCache.loadOutbox()
        assertEquals(listOf("w1", "w2"), entries.map { it.word_id })
        assertEquals(listOf("know", "dont_know"), entries.map { it.rating })
        // Every event needs a distinct id — the server dedups on it.
        assertEquals(2, entries.map { it.event_id }.toSet().size)
    }

    @Test
    fun removeEvents_deletes_only_the_acked_ids() {
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.addResult(u, l, "w2", "know")
        OfflineCache.addResult(u, l, "w3", "skip")

        val acked = OfflineCache.loadOutbox().take(2).map { it.event_id }.toSet()
        OfflineCache.removeEvents(acked)

        val left = OfflineCache.loadOutbox()
        assertEquals(1, left.size)
        assertEquals("w3", left[0].word_id)
    }

    @Test
    fun removeEvents_with_unknown_ids_is_a_no_op() {
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.removeEvents(setOf("not-a-real-event-id"))
        assertEquals(1, OfflineCache.pendingCount())
    }

    @Test
    fun outbox_survives_many_appends_in_order() {
        repeat(25) { OfflineCache.addResult(u, l, "w$it", "know") }
        val entries = OfflineCache.loadOutbox()
        assertEquals(25, entries.size)
        // ts is a zero-padded millis string, so lexicographic order == chronological.
        assertEquals(entries.map { it.ts }.sorted(), entries.map { it.ts })
    }

    // ── AudioCache on disk ───────────────────────────────────────────────────

    @Test
    fun cachedFile_is_null_until_a_file_exists_then_returns_it() {
        val path = "sounds/he/gtts/15.mp3"
        assertNull(AudioCache.cachedFile(path))

        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val dir = File(ctx.filesDir, "sounds").apply { mkdirs() }
        File(dir, AudioCache.fileNameFor(path)).writeBytes(byteArrayOf(1, 2, 3))

        assertNotNull(AudioCache.cachedFile(path))
        assertEquals(1, AudioCache.cachedCount())
    }

    @Test
    fun cachedFile_ignores_empty_files() {
        val path = "sounds/he/gtts/16.mp3"
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val dir = File(ctx.filesDir, "sounds").apply { mkdirs() }
        File(dir, AudioCache.fileNameFor(path)).createNewFile()   // zero length

        assertNull("a 0-byte file must not count as cached", AudioCache.cachedFile(path))
    }

    @Test
    fun sound_source_is_the_cached_file_when_there_is_one_and_the_server_otherwise() {
        // Офлайн-карточка обязана играть с диска: пока источник выбирался как
        // «всегда по сети», звук офлайн молчал, хотя файлы уже были скачаны.
        BLSClient.init("https://bls.example:8531")
        val path = "sounds/he/gtts/42.mp3"

        assertEquals(
            "без кеша играем по сети",
            "https://bls.example:8531/sounds/$path", AudioCache.sourceFor(path),
        )

        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val dir = File(ctx.filesDir, "sounds").apply { mkdirs() }
        val cached = File(dir, AudioCache.fileNameFor(path)).apply { writeBytes(byteArrayOf(1, 2, 3)) }

        assertEquals("скачанный файл важнее сети", cached.absolutePath, AudioCache.sourceFor(path))
    }

    @Test
    fun cachedCount_excludes_in_flight_tmp_files() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val dir = File(ctx.filesDir, "sounds").apply { mkdirs() }
        File(dir, "a.mp3").writeBytes(byteArrayOf(1))
        File(dir, "b.mp3.tmp").writeBytes(byteArrayOf(1))
        assertEquals(1, AudioCache.cachedCount())
    }

    // ── engine ───────────────────────────────────────────────────────────────

    @Test
    fun engine_advances_through_the_bundle_and_reports_the_end() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2), word("w3", 3))))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)

        assertEquals("w1", engine.currentWordId())
        assertTrue(engine.hasCurrent())
        engine.advance()
        assertEquals("w2", engine.currentWordId())
        engine.advance()
        assertEquals("w3", engine.currentWordId())
        assertTrue(!engine.atEnd())
        engine.advance()
        assertTrue("cursor past the last word must report atEnd", engine.atEnd())
        assertNull(engine.currentWordId())
    }

    @Test
    fun engine_serves_both_card_sides_for_the_current_word() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2))))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)

        assertEquals(false, engine.frontCard()?.show_answer)
        assertEquals(true, engine.answerCard()?.show_answer)
        // Both sides must describe the same position in the session.
        assertEquals(engine.frontCard()?.meta?.session_pos, engine.answerCard()?.meta?.session_pos)
    }

    @Test
    fun engine_positionAtWord_jumps_to_the_matching_word() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2), word("w3", 3))))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)

        assertTrue("встали на слово — это успех", engine.positionAtWord("w3"))
        assertEquals("w3", engine.currentWordId())
        assertTrue("пустой id — «остаёмся где стояли», это тоже успех",
            engine.positionAtWord(null))
        assertEquals("w3", engine.currentWordId())
    }

    @Test
    fun engine_positionAtWord_with_unknown_id_keeps_the_current_position() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2))))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)
        val before = engine.currentWordId()

        // Провал обязан быть виден вызывающему: он стоит на другом слове, чем
        // было на экране, и записывать за него оценку нельзя.
        assertFalse("слова нет в партии — это не успех", engine.positionAtWord("no-such-word"))
        assertEquals(before, engine.currentWordId())
    }

    @Test
    fun engine_record_writes_the_current_word_into_the_outbox() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2))))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)

        engine.record("know")
        engine.advance()
        engine.record("dont_know")

        val entries = OfflineCache.loadOutbox()
        assertEquals(listOf("w1", "w2"), entries.map { it.word_id })
        assertEquals(listOf("know", "dont_know"), entries.map { it.rating })
    }

    @Test
    fun resetting_the_cursor_makes_the_engine_start_over() {
        // What "🔄 Начать заново" must do while offline: rewind to the first word.
        // Previously restart fell through to enterOfflineFromStore(), which positions
        // at lastWordId, so the user stayed on the same word.
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2), word("w3", 3))))
        OfflineEngine(OfflineCache.loadBundle(u, l)!!).apply { advance(); advance() }
        assertEquals("w3", OfflineEngine.fromStore(u, l)!!.currentWordId())

        OfflineCache.saveCursor(u, l, 0)

        val restarted = OfflineEngine.fromStore(u, l)
        assertNotNull(restarted)
        assertEquals("w1", restarted!!.currentWordId())
        assertTrue(restarted.hasCurrent())
    }

    @Test
    fun engine_advance_persists_the_cursor_so_a_restart_resumes() {
        OfflineCache.saveBundle(StoredBundle(u, l, listOf(word("w1", 1), word("w2", 2), word("w3", 3))))
        OfflineEngine(OfflineCache.loadBundle(u, l)!!).apply { advance(); advance() }

        // Simulate the app being reopened: rebuild the engine from disk.
        val resumed = OfflineEngine.fromStore(u, l)
        assertNotNull(resumed)
        assertEquals("w3", resumed!!.currentWordId())
    }
}
