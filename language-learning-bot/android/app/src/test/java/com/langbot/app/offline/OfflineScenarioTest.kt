package com.langbot.app.offline

import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.network.BundleWord
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardMeta
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File

/**
 * Сценарные тесты офлайна: целые маршруты пользователя, а не отдельные методы.
 *
 * Все три бага, которые находил пользователь руками, были последовательностями:
 * номер слова не менялся, звук не грузился, «Начать заново» возвращало на то же
 * слово. Тест одного метода такое не видит — нужен прогон цепочки шагов.
 *
 * Всё на JVM: Robolectric даёт Context с настоящим filesDir, MockWebServer
 * изображает BLS. Эмулятор не нужен.
 */
@RunWith(RobolectricTestRunner::class)
class OfflineScenarioTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        AudioCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        File(ctx.filesDir, "sounds").deleteRecursively()

        server = MockWebServer()
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() = server.shutdown()

    // ── строители ────────────────────────────────────────────────────────────

    private fun meta(pos: Int) = CardMeta(
        word_number = pos, session_pos = pos, session_total = 10,
        correct_count = 0, incorrect_count = 0,
        pending_result = null, score_badge = null,
    )

    /** Кнопки со «штампом» сервера — так их отдаёт BLS card_builder. */
    private fun buttons(showAnswer: Boolean) =
        if (!showAnswer) listOf(
            CardButton("know", "Знаю", "success", "know", "submit", "know"),
            CardButton("show_answer", "Не знаю", "warn", null, "reveal_answer", null),
        ) else listOf(
            CardButton("rate", "Дальше", "success", "dont_know", "submit", "dont_know"),
        )

    private fun card(showAnswer: Boolean, pos: Int) = Card(
        show_answer = showAnswer,
        content = emptyList(),
        buttons = buttons(showAnswer),
        meta = meta(pos),
    )

    private fun word(i: Int) = BundleWord(
        word_id = "w$i", word_number = i,
        card_front = card(false, i), card_answer = card(true, i),
        sounds = listOf("sounds/he/gtts/$i.mp3"),
    )

    private fun bundle(n: Int) = StoredBundle(u, l, (1..n).map { word(it) }, cursor = 0)

    /** Что записал бы StudyActivity для нажатой кнопки — та же логика, что в handleOfflineAction. */
    private fun ratingFor(btn: CardButton) =
        btn.offline_rating ?: OfflineSemantics.ratingFor(btn.id, btn.rating)

    // ── сценарии ─────────────────────────────────────────────────────────────

    @Test
    fun full_offline_session_accumulates_results_then_syncs_when_network_returns() {
        OfflineCache.saveBundle(bundle(3))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)

        // Пользователь отвечает на три слова: знаю, не знаю, знаю.
        val answers = listOf("know", "dont_know", "know")
        for (r in answers) {
            assertTrue("сессия не должна кончиться раньше времени", engine.hasCurrent())
            engine.record(r)
            engine.advance()
        }
        assertTrue("после трёх слов бандл исчерпан", engine.atEnd())

        val queued = OfflineCache.loadOutbox()
        assertEquals(3, queued.size)
        assertEquals(listOf("w1", "w2", "w3"), queued.map { it.word_id })
        assertEquals(answers, queued.map { it.rating })

        // Сеть вернулась — очередь уходит на сервер и пустеет.
        val ids = queued.map { it.event_id }
        server.enqueue(MockResponse().setResponseCode(200).setBody(
            """{"acks":[${ids.joinToString(",") { """{"event_id":"$it","status":"ok"}""" }}]}"""))

        runBlocking { OutboxSync.flush() }

        val req = server.takeRequest()
        assertTrue(req.path!!, req.path!!.endsWith("/results/batch"))
        assertEquals("после успешной отправки очередь пуста", 0, OfflineCache.pendingCount())
    }

    @Test
    fun results_survive_a_failed_sync_and_go_out_on_the_next_attempt() {
        OfflineCache.saveBundle(bundle(2))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)
        engine.record("know"); engine.advance()
        engine.record("dont_know"); engine.advance()

        // Первая попытка — сервер лежит. Ничего терять нельзя.
        server.enqueue(MockResponse().setResponseCode(500))
        runBlocking { OutboxSync.flush() }
        assertEquals("при ошибке сервера результаты обязаны остаться", 2, OfflineCache.pendingCount())

        // Вторая попытка — сервер ожил.
        val ids = OfflineCache.loadOutbox().map { it.event_id }
        server.enqueue(MockResponse().setResponseCode(200).setBody(
            """{"acks":[${ids.joinToString(",") { """{"event_id":"$it","status":"ok"}""" }}]}"""))
        runBlocking { OutboxSync.flush() }
        assertEquals(0, OfflineCache.pendingCount())
    }

    @Test
    fun restart_offline_rewinds_to_the_first_word() {
        // Тот самый баг: «Начать заново» без сети возвращало на то же слово,
        // потому что движок позиционировался по lastWordId, а курсор не сбрасывался.
        OfflineCache.saveBundle(bundle(5))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)
        repeat(3) { engine.advance() }
        assertEquals("w4", OfflineEngine.fromStore(u, l)!!.currentWordId())

        // Что делает restartSession: сбрасывает курсор.
        OfflineCache.saveCursor(u, l, 0)

        val restarted = OfflineEngine.fromStore(u, l)!!
        assertEquals("w1", restarted.currentWordId())
        assertEquals(1, restarted.frontCard()!!.meta.session_pos)
    }

    @Test
    fun session_position_advances_across_the_whole_bundle() {
        // Баг «1 из N на каждом слове» был серверным, но клиент обязан показывать
        // то, что пришло. Здесь фиксируем: позиции идут по порядку и не повторяются.
        OfflineCache.saveBundle(bundle(6))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)

        val seen = mutableListOf<Int>()
        while (engine.hasCurrent()) {
            seen.add(engine.frontCard()!!.meta.session_pos)
            engine.advance()
        }
        assertEquals(listOf(1, 2, 3, 4, 5, 6), seen)
        assertEquals("позиции обязаны быть уникальными", seen.size, seen.toSet().size)
    }

    @Test
    fun app_restart_resumes_where_the_user_stopped() {
        OfflineCache.saveBundle(bundle(4))
        OfflineEngine(OfflineCache.loadBundle(u, l)!!).apply {
            record("know"); advance()
            record("know"); advance()
        }

        // Приложение закрыли и открыли снова — движок собирается с диска.
        val resumed = OfflineEngine.fromStore(u, l)
        assertNotNull(resumed)
        assertEquals("w3", resumed!!.currentWordId())
        assertEquals("накопленные результаты не теряются", 2, OfflineCache.pendingCount())
    }

    @Test
    fun button_semantics_come_from_the_server_stamp_not_from_the_client() {
        // Дедуп бизнес-логики: BLS штампует offline_effect/offline_rating,
        // клиент их только читает. Если сервер сказал «skip» — пишем skip,
        // даже когда локальное правило для этой кнопки сказало бы другое.
        val serverSaysSkip = CardButton("know", "Знаю", "success", "know", "submit", "skip")
        assertEquals("skip", ratingFor(serverSaysSkip))

        // А для старого бандла без штампов работает запасная логика.
        val legacy = CardButton("know", "Знаю", "success", "know", null, null)
        assertEquals("know", ratingFor(legacy))
        assertEquals("submit", OfflineSemantics.effectFor("know"))
        assertEquals("reveal_answer", OfflineSemantics.effectFor("show_answer"))
        assertNull("незнакомую кнопку офлайн игнорирует", OfflineSemantics.effectFor("unknown"))
    }

    @Test
    fun answering_through_server_stamped_buttons_records_the_right_ratings() {
        OfflineCache.saveBundle(bundle(2))
        val engine = OfflineEngine(OfflineCache.loadBundle(u, l)!!)

        // Первое слово — нажали «Знаю» на вопросной стороне.
        val know = engine.frontCard()!!.buttons.first { it.id == "know" }
        engine.record(ratingFor(know)); engine.advance()

        // Второе — «Не знаю», затем «Дальше» с ответной стороны.
        val rate = engine.answerCard()!!.buttons.first { it.id == "rate" }
        engine.record(ratingFor(rate)); engine.advance()

        assertEquals(listOf("know", "dont_know"), OfflineCache.loadOutbox().map { it.rating })
    }

    @Test
    fun sounds_of_every_word_in_the_bundle_are_known_upfront() {
        // Префетч берёт звуки ВСЕХ слов бандла, а не только текущего —
        // иначе офлайн озвучены будут первые несколько слов.
        OfflineCache.saveBundle(bundle(5))
        val stored = OfflineCache.loadBundle(u, l)!!

        val all = stored.words.flatMap { it.sounds }
        assertEquals(5, all.size)
        assertEquals(5, all.toSet().size)
        assertTrue(all.all { it.isNotBlank() })
        // Ни один ещё не скачан — кеш пуст, плеер обязан уметь это пережить.
        assertTrue(stored.words.all { w -> w.sounds.all { AudioCache.cachedFile(it) == null } })
    }
}
