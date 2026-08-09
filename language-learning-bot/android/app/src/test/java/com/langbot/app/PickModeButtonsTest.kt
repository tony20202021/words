package com.langbot.app

import android.content.Intent
import android.os.Looper
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
import android.widget.LinearLayout
import java.io.File

/**
 * Пик-режим: кнопки под вариантами рисуются из карточки, а не зашиты в экран.
 *
 * Раньше «❓ Не знаю» была написана прямо в StudyActivity, а card.buttons в
 * пик-режиме не читался вовсе — ветка пик-режима выходила раньше цикла по
 * кнопкам. Вместе с массивом пропадала «Пропускать»: настройка
 * show_skip_button в пик-режиме молча не работала, и снять с слова пометку
 * «пропущено», находясь в пик-режиме, было нечем.
 *
 * Тест поведенческий: Robolectric поднимает Activity, MockWebServer изображает
 * BLS, кнопки читаются из реального buttonRow.
 */
@RunWith(RobolectricTestRunner::class)
class PickModeButtonsTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"
    private val gson = Gson()

    /** Кнопки, которые «сервер» кладёт в карточку пик-режима. */
    private var serverButtons: List<CardButton> = emptyList()

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
                    MockResponse().setResponseCode(200).setBody(
                        gson.toJson(SessionResponse(session_id = "sid-1", card = pickCard()))
                    )
                } else {
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

    private fun pickCard() = Card(
        show_answer = false,
        content = listOf(CardItem("foreign", "ספר")),
        buttons = serverButtons,
        meta = CardMeta(
            word_id = "w1", word_number = 1, session_pos = 1, session_total = 10,
            correct_count = 0, incorrect_count = 0, pending_result = null, score_badge = null,
        ),
        pick_options = PickOptions(
            target_modality = "translation",
            options = listOf(
                PickOption("w1", "книга", true, "know"),
                PickOption("w2", "лошадь", false, "dont_know"),
            ),
        ),
    )

    private fun launchStudy(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", l)
            .putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
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

    private fun buttonTexts(a: StudyActivity): List<String> {
        val row = a.findViewById<LinearLayout>(R.id.buttonRow)
        val out = mutableListOf<String>()
        fun walk(v: android.view.View) {
            if (v is MaterialButton) out.add(v.text.toString())
            if (v is LinearLayout) (0 until v.childCount).forEach { walk(v.getChildAt(it)) }
        }
        walk(row)
        return out
    }

    private fun textsAfterLaunch(): List<String> {
        val a = launchStudy()
        pumpUntil("карточка пик-режима отрисована") {
            buttonTexts(a).any { it.contains("Выбрать") || it.contains("книга") }
        }
        return buttonTexts(a)
    }

    private val dontKnow =
        CardButton("pick_dont_know", "❓ Не знаю", "outline-secondary", null,
                   "record_and_reveal", "dont_know")
    private val skip =
        CardButton("toggle_skip", "⏩ Пропускать", "outline-secondary", null, "submit", "skip")

    @Test
    fun `кнопка Пропускать доступна в пик-режиме`() {
        serverButtons = listOf(dontKnow, skip)
        val texts = textsAfterLaunch()
        assertTrue("«Пропускать» пропала, есть: $texts", texts.any { it.contains("Пропускать") })
        assertTrue("«Не знаю» пропала, есть: $texts", texts.any { it.contains("Не знаю") })
    }

    @Test
    fun `настройка показа кнопки Пропускать соблюдается`() {
        serverButtons = listOf(dontKnow)
        val texts = textsAfterLaunch()
        assertFalse("настройка выключена, а кнопка есть: $texts",
                    texts.any { it.contains("Пропускать") })
        assertTrue(texts.any { it.contains("Не знаю") })
    }

    @Test
    fun `текст кнопки берётся из карточки, а не зашит в экран`() {
        serverButtons = listOf(dontKnow.copy(text = "❓ Понятия не имею"))
        val texts = textsAfterLaunch()
        assertTrue("текст не из карточки: $texts", texts.any { it.contains("Понятия не имею") })
        assertFalse("зашитый текст всё ещё рисуется: $texts",
                    texts.any { it == "❓ Не знаю" })
    }

    @Test
    fun `состояние пропуска видно на кнопке`() {
        serverButtons = listOf(dontKnow, skip.copy(text = "⏩ Не пропускать"))
        val texts = textsAfterLaunch()
        assertTrue("нельзя понять, что слово уже пропущено: $texts",
                   texts.any { it.contains("Не пропускать") })
    }

    @Test
    fun `варианты ответа остаются на месте`() {
        serverButtons = listOf(dontKnow, skip)
        val texts = textsAfterLaunch()
        assertEquals("варианты ответа пропали: $texts", 2,
                     texts.count { it.contains("книга") || it.contains("лошадь") ||
                                   it.contains("Выбрать") })
    }
}
