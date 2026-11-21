package com.langbot.app

import android.content.Intent
import android.os.Looper
import android.view.ViewGroup
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.google.gson.Gson
import com.langbot.app.network.*
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.StoredBundle
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.*
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.android.controller.ActivityController
import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(RobolectricTestRunner::class)
class LocalStudyTransitionsTest {
    private val gson = Gson()
    private lateinit var server: MockWebServer
    private val release = CountDownLatch(1)
    private var activity: StudyActivity? = null
    private var controller: ActivityController<StudyActivity>? = null
    private val paths = Collections.synchronizedList(mutableListOf<String>())
    private var shownQuiz: PickOptions? = null
    @Volatile private var failSync = false
    @Volatile private var failSession = false
    @Volatile private var serverQuestionId = "w1"
    private var serverSessionTotal = 4
    private var serverSessionPosition = 1

    private fun card(id: String, answer: Boolean = false, known: Boolean = false): Card = Card(
        show_answer = answer,
        content = listOf(CardItem(if (answer) "translation" else "foreign", if (answer) "answer-$id" else "question-$id")),
        buttons = when {
            known -> listOf(CardButton("rate", "Next", "success", rating = "know", offline_effect = "advance"),
                CardButton("reconsider", "Correct", "outline-danger", offline_effect = "reveal_question", offline_rating = "dont_know"),
                CardButton("toggle_skip", "Skip", "outline-secondary", offline_effect = "submit", offline_rating = "skip"))
            answer -> listOf(CardButton("rate", "Next", "success", rating = "dont_know", offline_effect = "submit", offline_rating = "dont_know"),
                CardButton("toggle_skip", "Skip", "outline-secondary", offline_effect = "submit", offline_rating = "skip"))
            else -> listOf(CardButton("know", "Know", "success", offline_effect = "record_and_reveal", offline_rating = "know"),
                CardButton("show_answer", "Reveal", "outline-danger", offline_effect = "reveal_answer"))
        }, meta = CardMeta(word_id = id, word_number = id.removePrefix("w").toInt(), session_total = 4, words_for_today = 4))

    @Before fun setup() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(context)
        context.filesDir.listFiles()?.filter { it.isFile }?.forEach { it.delete() }
        UserPrefs.saveUserId(context, "u")
        val words = (1..4).map { n -> BundleWord(word_id = "w$n", word_number = n,
            card_front = card("w$n"), card_answer = card("w$n", true), card_known = card("w$n", true, true)) }
        OfflineCache.saveBundle(StoredBundle("u", "l", words, requestedSize = 100, savedAt = System.currentTimeMillis()))
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path.orEmpty()
                paths.add(path)
                if (path.contains("results/batch")) {
                    if (failSync) return MockResponse().setResponseCode(500)
                    release.await(10, TimeUnit.SECONDS)
                    val body = gson.fromJson(request.body.readUtf8(), ResultsBatchRequest::class.java)
                    val acks = body.events.joinToString(",") { "{\"event_id\":\"${it.event_id}\",\"status\":\"ok\"}" }
                    return MockResponse().setBody("{\"acks\":[$acks]}")
                }
                if (path.contains("/session/") && request.method == "GET") {
                    if (failSession) return MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START)
                    return MockResponse().setBody(gson.toJson(SessionResponse(session_id = "sid", card = card(serverQuestionId).copy(pick_options = shownQuiz,
                        meta = card(serverQuestionId).meta.copy(session_pos = serverSessionPosition,
                            session_total = serverSessionTotal, words_for_today = serverSessionTotal,
                            show_session_counter = true,
                            session_counter_text = "(в сессии: $serverSessionPosition из $serverSessionTotal)")))))
                }
                if (path.endsWith("/know") || path.endsWith("/show_answer")) {
                    release.await(10, TimeUnit.SECONDS)
                    return MockResponse().setBody(gson.toJson(SessionResponse(session_id = "sid", card = card("w1", true, true))))
                }
                return MockResponse().setResponseCode(404)
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }
    @After fun cleanup() {
        release.countDown()
        controller?.pause()?.stop()?.destroy()
        shadowOf(Looper.getMainLooper()).idle()
        server.shutdown()
    }
    private fun open(expectedWord: String = "w1") {
        controller = Robolectric.buildActivity(StudyActivity::class.java,
            Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java).putExtra("language_id", "l")).setup()
        activity = controller!!.get()
        Screenshots.pumpUntil("question rendered") { texts().contains("question-$expectedWord") }
    }
    private fun texts(): String = activity?.let {
        Screenshots.texts(it.findViewById<ViewGroup>(R.id.cardContent)).joinToString("\n") { v -> v.text.toString() }
    }.orEmpty()
    private fun tap(label: String) {
        Screenshots.texts(activity!!.findViewById<ViewGroup>(R.id.buttonRow))
            .filterIsInstance<MaterialButton>().first { it.text.toString() == label }.performClick()
        shadowOf(Looper.getMainLooper()).idle()
    }
    @Test fun cached_question_reveals_answer_before_network_completes() {
        open(); tap("Know")
        assertTrue("old question stayed visible while network is blocked", texts().contains("answer-w1"))
        assertEquals(listOf("w1" to "know"), OfflineCache.loadOutbox().map { it.word_id to it.rating })
    }
    @Test fun reveal_records_unknown_immediately_without_waiting_for_next() {
        open(); tap("Reveal")
        assertTrue(texts().contains("answer-w1"))
        assertEquals(listOf("dont_know"), OfflineCache.loadOutbox().map { it.rating })
    }
    @Test fun rapid_transitions_and_late_ack_keep_the_current_card_and_counts() {
        open(); tap("Know"); tap("Next")
        assertTrue("advance waited for server", texts().contains("question-w2"))
        tap("Reveal"); tap("Next")
        assertTrue(texts().contains("question-w3"))
        assertEquals(listOf("w1" to "know", "w2" to "dont_know"), OfflineCache.loadOutbox().map { it.word_id to it.rating })
        val before = texts()
        release.countDown()
        Screenshots.pumpUntil("sync completed") { OfflineCache.pendingCount() == 0 }
        shadowOf(Looper.getMainLooper()).idle()
        assertEquals("late network response changed current card", before, texts())
        tap("Know"); tap("Next")
        assertTrue("reconnection started a blocking reload", texts().contains("question-w4"))
        assertEquals(0, paths.count { it.endsWith("/know") || it.endsWith("/rate") })
    }
    @Test fun shown_quiz_options_determine_the_rating_not_the_cached_question() {
        shownQuiz = PickOptions("translation", listOf(PickOption("shown-right", "Correct shown option", true), PickOption("shown-wrong", "Wrong shown option", false)))
        open()
        Screenshots.texts(activity!!.findViewById<ViewGroup>(R.id.buttonRow)).filterIsInstance<MaterialButton>()
            .first { it.text.toString().contains("Correct shown option") }.performClick()
        shadowOf(Looper.getMainLooper()).idle()
        assertTrue(texts().contains("answer-w1"))
        assertEquals("know", OfflineCache.loadOutbox().single().rating)
    }
    @Test fun missing_current_word_keeps_network_fallback_and_does_not_rate_another_word() {
        val bundle = OfflineCache.loadBundle("u", "l")!!
        OfflineCache.saveBundle(bundle.copy(words = bundle.words.drop(1)))
        open(); tap("Know")
        assertTrue(texts().contains("question-w1")); assertTrue(OfflineCache.loadOutbox().isEmpty())
        release.countDown()
        Screenshots.pumpUntil("server answer") { texts().contains("answer-w1") }
    }
    @Test fun correction_after_ack_replaces_the_local_rating_without_counting_twice() {
        open(); tap("Know"); release.countDown()
        Screenshots.pumpUntil("known result sent") { OfflineCache.pendingCount() == 0 }
        failSync = true
        tap("Correct")
        assertTrue(texts().contains("question-w2"))
        assertEquals("dont_know", OfflineCache.loadOutbox().last().rating)
        val all = Screenshots.texts(activity!!.findViewById<ViewGroup>(R.id.swipeRefresh)).joinToString("\n") { it.text.toString() }
        assertTrue("known count did not decrease: $all", Regex("0 правильн").containsMatchIn(all))
        assertTrue("unknown count did not increase: $all", all.contains("1 ошиб"))
    }
    // Владелец (18.11.2026): «на карточке вопроса — просто обновляет экран, на
    // карточке ответа — переходит на следующее слово». Ответ уходит на сервер
    // пачкой, и пачка двигает серверную сессию дальше: спроси обновление
    // сервер — он отвечает уже следующим словом.
    private fun pullDown() {
        activity!!.refreshForTest()
        Screenshots.pumpUntil("обновление закончилось") {
            activity!!.findViewById<android.view.View>(R.id.loadingBar).visibility != android.view.View.VISIBLE
        }
        shadowOf(Looper.getMainLooper()).idle()
    }

    @Test fun pulling_down_on_the_answer_keeps_the_answer_instead_of_moving_on() {
        open(); tap("Know"); release.countDown()
        Screenshots.pumpUntil("ответ отправлен") { OfflineCache.pendingCount() == 0 }
        serverQuestionId = "w2"                    // пачка сдвинула серверную сессию
        pullDown()
        assertTrue("обновление на ответе перешло к другому слову: ${texts()}",
            texts().contains("answer-w1"))
        // Отмена «ой, все-таки не знаю» на месте: ответ тот же, не урезанный.
        failSync = true                            // поправку оставить в очереди
        tap("Correct")
        assertTrue(texts().contains("question-w2"))
        assertEquals("dont_know", OfflineCache.loadOutbox().last().rating)
    }

    // Владелец (21.11.2026): «„потянуть вниз“ на карточке вопроса иногда меняет
    // тип вопроса». Вопрос показан из партии на телефоне, а тип вопроса для
    // слова партия и серверная сессия выбирают каждая своим жребием. Обновление
    // рисовало серверный вариант — и когда жребии расходились, тот же вопрос
    // превращался, например, в выбор из вариантов.
    @Test fun pulling_down_on_a_question_keeps_its_kind_when_the_server_is_on_the_same_word() {
        open(); tap("Know"); tap("Next"); release.countDown()
        Screenshots.pumpUntil("ответ отправлен") { OfflineCache.pendingCount() == 0 }
        assertTrue(texts().contains("question-w2"))
        serverQuestionId = "w2"                    // сервер на том же слове,
        shownQuiz = PickOptions("translation", listOf(   // но у него жребий — выбор
            PickOption("x", "Correct shown option", true), PickOption("y", "Wrong shown option", false)))
        pullDown()
        val labels = Screenshots.texts(activity!!.findViewById<ViewGroup>(R.id.buttonRow))
            .filterIsInstance<MaterialButton>().map { it.text.toString() }
        assertTrue("обновление сменило слово: ${texts()}", texts().contains("question-w2"))
        assertFalse("обновление сменило тип вопроса: $labels", labels.any { it.contains("shown option") })
        tap("Know")                                // и ответ идёт как раньше, на месте
        assertTrue(texts().contains("answer-w2"))
    }

    @Test fun pulling_down_on_a_question_follows_the_server_to_another_word() {
        // Прогресс общий для всех платформ: если на сервере уже другое слово
        // (занимались в боте или вебе), обновление его и показывает.
        open(); tap("Know"); tap("Next"); release.countDown()
        Screenshots.pumpUntil("ответ отправлен") { OfflineCache.pendingCount() == 0 }
        serverQuestionId = "w3"
        pullDown()
        assertTrue(texts().contains("question-w3"))
    }

    @Test fun pulling_down_on_the_question_still_asks_the_server() {
        open()
        val asked = paths.count { it.contains("/session/") }
        pullDown()
        assertTrue("обновление на вопросе не спросило сервер",
            paths.count { it.contains("/session/") } > asked)
        assertTrue(texts().contains("question-w1"))
    }

    @Test fun a_stale_button_cannot_record_the_same_answer_twice() {
        open()
        val oldButton = Screenshots.texts(activity!!.findViewById<ViewGroup>(R.id.buttonRow))
            .filterIsInstance<MaterialButton>().first { it.text.toString() == "Know" }
        oldButton.performClick()
        oldButton.performClick()
        assertTrue(texts().contains("answer-w1"))
        assertEquals(1, OfflineCache.loadOutbox().size)
    }

    @Test fun acknowledged_progress_survives_reopening_without_network() {
        open(); tap("Know"); tap("Next"); release.countDown()
        Screenshots.pumpUntil("acknowledged") { OfflineCache.pendingCount() == 0 }
        controller!!.pause().stop().destroy()
        shadowOf(Looper.getMainLooper()).idle()
        failSession = true
        open("w2")
        val all = Screenshots.texts(activity!!.findViewById<ViewGroup>(R.id.swipeRefresh)).joinToString("\n") { it.text.toString() }
        assertTrue("lost acknowledged local score: $all", Regex("1 правильн").containsMatchIn(all))
    }

    @Test fun cache_exhaustion_loads_more_words_only_after_results_are_confirmed() {
        open()
        repeat(4) { tap("Know"); tap("Next") }
        assertEquals(4, OfflineCache.pendingCount())
        assertEquals("no reload while there are unsent answers", 1, paths.count { it.contains("/session/") && !it.endsWith("/know") })
        serverQuestionId = "w5"
        release.countDown()
        Screenshots.pumpUntil("next batch after ack") { texts().contains("question-w5") }
    }

    @Test fun skip_replaces_a_revealed_unknown_answer_before_ack() {
        open(); tap("Reveal"); tap("Skip")
        assertTrue(texts().contains("question-w2"))
        assertEquals(listOf("dont_know", "skip"), OfflineCache.loadOutbox().map { it.rating })
    }

    @Test fun skip_replaces_a_known_answer_after_ack() {
        open(); tap("Know"); release.countDown()
        Screenshots.pumpUntil("known acknowledged") { OfflineCache.pendingCount() == 0 }
        failSync = true
        tap("Skip")
        assertTrue(texts().contains("question-w2"))
        assertEquals("skip", OfflineCache.loadOutbox().last().rating)
    }

    private fun largeCache(sessionTotal: Int = 5) {
        val original = OfflineCache.loadBundle("u", "l")!!
        val words = (1..300).map { n ->
            fun cached(answer: Boolean = false, known: Boolean = false): Card {
                val c = card("w$n", answer, known)
                return c.copy(meta = c.meta.copy(session_pos = n, session_total = sessionTotal,
                    words_for_today = sessionTotal, show_session_counter = true))
            }
            BundleWord("w$n", n, cached(), cached(true), cached(true, true))
        }
        OfflineCache.saveBundle(original.copy(words = words))
    }

    private fun allTexts(): String = Screenshots.texts(activity!!.findViewById<ViewGroup>(R.id.swipeRefresh))
        .joinToString("\n") { it.text.toString() }

    @Test fun the_fifth_of_five_does_not_become_the_fifth_of_300() {
        largeCache()
        serverQuestionId = "w5"; serverSessionPosition = 5; serverSessionTotal = 5
        open("w5"); tap("Reveal")
        assertTrue(allTexts(), texts().contains("завершающее в текущей сессии: 5"))
        assertFalse(allTexts(), allTexts().contains("из 300"))
        assertTrue(allTexts(), allTexts().contains("готово 1 из 5"))
        release.countDown()
        Screenshots.pumpUntil("ACK") { OfflineCache.pendingCount() == 0 }
        assertFalse(allTexts(), allTexts().contains("из 300"))
    }

    @Test fun a_new_cache_does_not_reset_global_session_position() {
        largeCache(sessionTotal = 250)
        serverQuestionId = "w3"; serverSessionPosition = 105; serverSessionTotal = 250
        open("w3"); tap("Reveal")
        assertTrue(allTexts(), texts().contains("в сессии: 105 из 250"))
        tap("Next")
        assertTrue(allTexts(), texts().contains("в сессии: 106 из 250"))
    }

    @Test fun global_session_position_survives_ack_and_reopening_offline() {
        largeCache(sessionTotal = 250)
        serverQuestionId = "w3"; serverSessionPosition = 105; serverSessionTotal = 250
        open("w3"); tap("Reveal"); tap("Next"); release.countDown()
        Screenshots.pumpUntil("ACK") { OfflineCache.pendingCount() == 0 }
        controller!!.pause().stop().destroy()
        shadowOf(Looper.getMainLooper()).idle()
        failSession = true
        open("w4")
        assertTrue(allTexts(), texts().contains("в сессии: 106 из 250"))
        assertFalse(allTexts(), allTexts().contains("из 300"))
    }

    @Test fun refresh_and_reentering_local_mode_keep_the_session_total() {
        largeCache()
        serverSessionTotal = 5
        open(); tap("Know"); tap("Next"); release.countDown()
        Screenshots.pumpUntil("ACK") { OfflineCache.pendingCount() == 0 }
        serverQuestionId = "w2"; serverSessionPosition = 2
        activity!!.refreshForTest()
        Screenshots.pumpUntil("server refreshed progress") {
            OfflineCache.loadProgress("u", "l")?.localRatings == null
        }
        assertTrue(allTexts(), texts().contains("в сессии: 2 из 5"))
        tap("Reveal"); tap("Next")
        assertTrue(allTexts(), texts().contains("в сессии: 3 из 5"))
    }

}
