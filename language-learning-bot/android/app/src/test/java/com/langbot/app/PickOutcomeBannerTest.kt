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
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardItem
import com.langbot.app.network.CardMeta
import com.langbot.app.network.PickOption
import com.langbot.app.network.PickOptions
import com.langbot.app.network.SessionResponse
import com.langbot.app.offline.OfflineCache
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

/**
 * «Не знаю» — это не ошибка, и экран не должен называть её неверным ответом.
 *
 * Жалоба владельца: «в пик-режиме я выбираю пункт "не знаю", на следующем
 * экране статус "неправильно" — нелогично, я честно признался, что не знаю».
 *
 * Состояний теперь три, а не два: угадал, промахнулся, признался. Раньше
 * признание и промах складывались в один Boolean и выглядели одинаково.
 */
@RunWith(RobolectricTestRunner::class)
class PickOutcomeBannerTest {

    private lateinit var server: MockWebServer
    private val gson = Gson()

    /** Что ответить на выбор варианта: промах помечается last_wrong_distractor_id. */
    private var answerWrong = false

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        UserPrefs.saveUserId(ctx, "user-1")

        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    path.contains("pick_answer") -> ok(answerCard())
                    path.startsWith("/session/") && request.method == "GET" -> ok(questionCard())
                    else -> MockResponse().setResponseCode(404)
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

    private fun ok(card: Card) = MockResponse().setResponseCode(200)
        .setBody(gson.toJson(SessionResponse(session_id = "sid-1", card = card)))

    private fun meta() = CardMeta(
        word_id = "w1", word_number = 1, session_pos = 1, session_total = 10,
        correct_count = 0, incorrect_count = 0, pending_result = null, score_badge = null,
    )

    private fun questionCard() = Card(
        show_answer = false,
        content = listOf(CardItem("foreign", "ספר")),
        buttons = listOf(CardButton("pick_dont_know", "❓ Не знаю", "outline-secondary",
                                    null, "record_and_reveal", "dont_know")),
        meta = meta(),
        pick_options = PickOptions(
            target_modality = "translation",
            options = listOf(PickOption("w1", "книга", true, "know"),
                             PickOption("w2", "лошадь", false, "dont_know")),
        ),
    )

    private fun answerCard() = Card(
        show_answer = true,
        content = listOf(CardItem("translation", "книга")),
        buttons = listOf(CardButton("rate", "➡️ Дальше", "success", "dont_know",
                                    "submit", "dont_know")),
        meta = meta(),
        last_wrong_distractor_id = if (answerWrong) "w2" else null,
    )

    private fun study(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        pumpUntil("карточка пик-режима отрисована") {
            buttons(a).any { it.text.contains("книга") || it.text.contains("Выбрать") }
        }
        return a
    }

    private fun pumpUntil(what: String, timeoutMs: Long = 15_000, cond: () -> Boolean) {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) return
            Thread.sleep(10)
        }
        fail("не дождались: $what")
    }

    private fun buttons(a: StudyActivity): List<MaterialButton> {
        val out = mutableListOf<MaterialButton>()
        fun walk(v: View) {
            if (v is MaterialButton) out.add(v)
            if (v is LinearLayout) (0 until v.childCount).forEach { walk(v.getChildAt(it)) }
        }
        walk(a.findViewById<LinearLayout>(R.id.buttonRow))
        return out
    }

    private fun banner(a: StudyActivity): TextView = a.findViewById(R.id.tvPickResult)

    private fun answerWith(a: StudyActivity, contains: String) {
        buttons(a).first { it.text.contains(contains) }.performClick()
        pumpUntil("экран показал итог ответа") {
            banner(a).visibility == View.VISIBLE
        }
    }

    @Test
    fun `признание в незнании не называется ошибкой`() {
        val a = study()
        answerWith(a, "Не знаю")
        val text = banner(a).text.toString()
        assertTrue("за честное «не знаю» экран отвечает «$text»", text.contains("Не знал"))
        assertFalse("«не знаю» названо неверным ответом: «$text»", text.contains("Неверно"))
    }

    @Test
    fun `промах по-прежнему называется промахом`() {
        answerWrong = true
        val a = study()
        answerWith(a, "книга")
        assertEquals("✗  Неверно", banner(a).text.toString())
    }

    @Test
    fun `верный ответ остаётся верным`() {
        answerWrong = false
        val a = study()
        answerWith(a, "книга")
        assertEquals("✓  Правильно!", banner(a).text.toString())
    }

    @Test
    fun `у признания свой цвет, не красный промаха`() {
        """
        Цвет — часть сообщения. Красный говорит «ошибка»; за признание в
        незнании краснеть не за что, поэтому фон у него свой.
        """
        answerWrong = true
        val wrong = study()
        answerWith(wrong, "книга")
        val wrongBg = (banner(wrong).background as? android.graphics.drawable.ColorDrawable)?.color

        val admitted = study()
        answerWith(admitted, "Не знаю")
        val admittedBg = (banner(admitted).background as? android.graphics.drawable.ColorDrawable)?.color

        assertTrue("цвет признания совпал с цветом ошибки", wrongBg != admittedBg)
    }
}
