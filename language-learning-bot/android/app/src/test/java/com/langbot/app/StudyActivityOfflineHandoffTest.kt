package com.langbot.app

import android.content.Intent
import android.os.Looper
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.google.gson.Gson
import com.langbot.app.network.BLSClient
import com.langbot.app.network.BundleWord
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardItem
import com.langbot.app.network.CardMeta
import com.langbot.app.network.SessionResponse
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.StoredBundle
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import java.io.File

/**
 * Стык «онлайн упал → офлайн» внутри самой StudyActivity.
 *
 * Зачем именно Activity, а не движок
 * ----------------------------------
 * Движок и кеш покрыты по отдельности, но переход между ними живёт в Activity:
 * там решается, на какое слово встать и применять ли к нему нажатие. Ошибка
 * здесь тихая — результат уходит на сервер молча и за чужое слово, экран при
 * этом выглядит нормально. Ровно этот случай и проверяем: занимались онлайн
 * словом, которого нет в офлайн-партии (партия скачана раньше, слово пришло из
 * новой), сеть отвалилась на нажатии — оценка не должна попасть в outbox.
 *
 * Всё на JVM: Robolectric поднимает Activity, MockWebServer изображает BLS,
 * «обрыв сети» — это shutdown() сервера (подключение отвергается сразу).
 */
@RunWith(RobolectricTestRunner::class)
class StudyActivityOfflineHandoffTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"
    private val gson = Gson()

    /** Карточка, которую отдаёт «сервер» на GET /session. */
    private var serverCardWordId = "zz"

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        File(ctx.filesDir, "sounds").deleteRecursively()
        UserPrefs.saveUserId(ctx, u)

        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return if (path.startsWith("/session/") && request.method == "GET") {
                    MockResponse().setResponseCode(200).setBody(gson.toJson(
                        SessionResponse(session_id = "sid-1", card = frontCard(serverCardWordId, 3))
                    ))
                } else if (path.endsWith("/know") && request.method == "POST") {
                    // Онлайн-ответ на слово: сервер отдаёт ответную сторону.
                    MockResponse().setResponseCode(200).setBody(gson.toJson(
                        SessionResponse(session_id = "sid-1", card = answerCard(serverCardWordId, 3))
                    ))
                } else {
                    // Всё остальное (префетч бандла, флаш outbox) в этом тесте
                    // не участвует: пусть не мешает и не переписывает кеш.
                    MockResponse().setResponseCode(404)
                }
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    // ── строители ────────────────────────────────────────────────────────────

    private fun meta(wordId: String, pos: Int) = CardMeta(
        word_id = wordId, word_number = pos, session_pos = pos, session_total = 10,
        correct_count = 0, incorrect_count = 0, pending_result = null, score_badge = null,
    )

    private fun frontCard(wordId: String, pos: Int) = Card(
        show_answer = false,
        content = listOf(CardItem("foreign", "слово-$wordId")),
        buttons = listOf(
            CardButton("know", "Знаю", "success", "know", "record_and_reveal", "know"),
            CardButton("show_answer", "Не знаю", "warn", null, "reveal_answer", null),
        ),
        meta = meta(wordId, pos),
    )

    private fun answerCard(wordId: String, pos: Int) = Card(
        show_answer = true,
        content = listOf(CardItem("translation", "перевод-$wordId")),
        buttons = listOf(CardButton("rate", "Дальше", "success", "dont_know", "submit", "dont_know")),
        meta = meta(wordId, pos),
    )

    private fun bundleOf(vararg ids: String) = StoredBundle(
        u, l,
        ids.mapIndexed { i, id ->
            BundleWord(id, i + 1, frontCard(id, i + 1), answerCard(id, i + 1))
        },
        cursor = 0,
    )

    // ── инструменты ──────────────────────────────────────────────────────────

    /** Прокрутить главный looper, пока условие не станет истинным. */
    private fun pumpUntil(what: String, timeoutMs: Long = 15_000, cond: () -> Boolean) {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) return
            Thread.sleep(10)
        }
        fail("не дождались: $what")
    }

    private fun launchStudy(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", l)
            .putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
    }

    private fun buttonRow(a: StudyActivity) = a.findViewById<LinearLayout>(R.id.buttonRow)

    private fun buttonTexts(a: StudyActivity): List<String> =
        (0 until buttonRow(a).childCount)
            .mapNotNull { buttonRow(a).getChildAt(it) as? MaterialButton }
            .map { it.text.toString() }

    private fun click(a: StudyActivity, text: String) {
        val row = buttonRow(a)
        val btn = (0 until row.childCount)
            .mapNotNull { row.getChildAt(it) as? MaterialButton }
            .firstOrNull { it.text.toString() == text }
            ?: fail("кнопка «$text» не найдена, есть: ${buttonTexts(a)}").let { return }
        btn.performClick()
    }

    private fun offlineBannerShown(a: StudyActivity): Boolean =
        a.findViewById<TextView>(R.id.tvStaleSession).let {
            it.visibility == View.VISIBLE && it.text.contains("Офлайн")
        }

    // ── сценарии ─────────────────────────────────────────────────────────────

    @Test
    fun answer_for_a_word_missing_from_the_bundle_is_not_recorded() {
        // Офлайн-партия скачана раньше: в ней w1..w3. Онлайн-сессия дошла до
        // слова zz из новой партии — в кеше его нет.
        OfflineCache.saveBundle(bundleOf("w1", "w2", "w3"))
        serverCardWordId = "zz"

        val activity = launchStudy()
        pumpUntil("карточка с сервера отрисована") { buttonTexts(activity).contains("Знаю") }

        // Сеть пропала ровно на нажатии.
        server.shutdown()
        click(activity, "Знаю")
        pumpUntil("переход в офлайн") { offlineBannerShown(activity) }

        assertEquals(
            "оценка за слово, которого нет в партии, ушла бы на сервер за чужое слово: " +
                    OfflineCache.loadOutbox().map { "${it.word_id}=${it.rating}" },
            0, OfflineCache.pendingCount(),
        )
        // Учиться при этом можно: движок встал на сохранённое место.
        assertTrue("офлайн должен продолжиться с сохранённого места",
            buttonTexts(activity).contains("Знаю"))
    }

    @Test
    fun answer_for_a_word_present_in_the_bundle_is_recorded_offline() {
        // Контроль: то же самое, но слово в партии есть — оценка обязана
        // сохраниться, и именно за него.
        OfflineCache.saveBundle(bundleOf("w1", "w2", "w3"))
        serverCardWordId = "w2"

        val activity = launchStudy()
        pumpUntil("карточка с сервера отрисована") { buttonTexts(activity).contains("Знаю") }

        server.shutdown()
        click(activity, "Знаю")
        pumpUntil("переход в офлайн") { offlineBannerShown(activity) }

        val out = OfflineCache.loadOutbox()
        assertEquals("ровно одна запись: $out", 1, out.size)
        assertEquals("w2", out.first().word_id)
        assertEquals("know", out.first().rating)
    }


    @Test
    fun first_step_into_offline_lands_on_the_question_of_the_next_word() {
        // Сценарий из отчёта: онлайн ответили на первое слово (увидели его
        // ответную сторону), нажали «Дальше» — и на этом пропала сеть.
        // Ожидание: вопрос ВТОРОГО слова. Ответная сторона означала бы, что
        // экран вопроса проскочили.
        OfflineCache.saveBundle(bundleOf("w1", "w2", "w3"))
        serverCardWordId = "w1"

        val activity = launchStudy()
        pumpUntil("вопрос первого слова") { buttonTexts(activity).contains("Знаю") }

        // Отвечаем ОНЛАЙН — сервер ещё жив.
        click(activity, "Знаю")
        pumpUntil("ответная сторона первого слова") { buttonTexts(activity).contains("Дальше") }

        // Сеть пропадает ровно на переходе к следующему слову.
        server.shutdown()
        click(activity, "Дальше")
        pumpUntil("переход в офлайн") { offlineBannerShown(activity) }

        val texts = buttonTexts(activity)
        assertTrue(
            "ожидался вопрос следующего слова, кнопки: $texts",
            texts.contains("Знаю"),
        )
        assertFalse(
            "показана ответная сторона — экран вопроса проскочили: $texts",
            texts.any { it.contains("Дальше") },
        )
    }

}
