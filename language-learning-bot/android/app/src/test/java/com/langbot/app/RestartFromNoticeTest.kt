package com.langbot.app

import android.content.Intent
import android.os.Looper
import android.view.View
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.google.gson.Gson
import com.langbot.app.network.BLSClient
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardItem
import com.langbot.app.network.CardMeta
import com.langbot.app.network.SessionResponse
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.shadows.ShadowDialog
import java.util.concurrent.CopyOnWriteArrayList

/**
 * Плашка советует перезапустить сессию — и даёт это сделать на месте.
 *
 * Жалоба владельца: «можно ли прямо в плашке с сообщением сделать кнопку или
 * ссылку обновить сессию, чтобы не выбирать дополнительно из меню».
 *
 * Совет без хода к действию — это полсовета: экран говорит, что делать, а
 * делать надо в другом месте, через меню из трёх точек.
 */
@RunWith(RobolectricTestRunner::class)
class RestartFromNoticeTest {

    private lateinit var server: MockWebServer
    private val gson = Gson()
    private val paths = CopyOnWriteArrayList<String>()

    /** Показывать ли плашку: ею управляет сервер, как и в жизни. */
    private var notice: String? =
        "⚠️ Ошибок в сессии: 10, лимит: 10. Рекомендуется перезапустить сессию."

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
                paths.add("${request.method} ${path.substringBefore('?')}")
                return when {
                    request.method == "DELETE" ->
                        MockResponse().setResponseCode(200).setBody("{}")
                    else -> MockResponse().setResponseCode(200)
                        .setBody(gson.toJson(SessionResponse(session_id = "sid-1", card = card())))
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

    private fun card() = Card(
        show_answer = false,
        restart_notice = notice,
        content = listOf(CardItem("foreign", "ספר")),
        buttons = listOf(CardButton("know", "✅ Знаю", "success", null, "submit", "know")),
        meta = CardMeta(word_id = "w1", word_number = 253, session_pos = 44,
                        session_total = 44, correct_count = 34, incorrect_count = 10),
    )

    private fun study(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        pumpUntil("карточка отрисована") { a.findViewById<View>(R.id.cardContent).let { it != null } }
        shadowOf(Looper.getMainLooper()).idle()
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

    private fun box(a: StudyActivity): View = a.findViewById(R.id.restartNotice)
    private fun button(a: StudyActivity): MaterialButton = a.findViewById(R.id.btnRestartNow)

    @Test
    fun `кнопка стоит в самой плашке и видна вместе с ней`() {
        val a = study()
        pumpUntil("плашка показана") { box(a).visibility == View.VISIBLE }
        assertEquals("кнопки не видно, хотя плашка на экране",
                     View.VISIBLE, button(a).visibility)
        assertTrue("кнопка не внутри плашки — она уедет вместе с другим содержимым",
                   generateSequence(button(a).parent) { (it as? View)?.parent }
                       .any { it === box(a) })
        val text = button(a).text.toString()
        assertTrue("по кнопке не понять, что она делает: «$text»", text.contains("заново"))
    }

    @Test
    fun `без плашки нет и кнопки`() {
        notice = null
        val a = study()
        assertEquals("плашка показана без повода", View.GONE, box(a).visibility)
    }

    @Test
    fun `нажатие спрашивает подтверждение, а не рушит круг молча`() {
        val a = study()
        pumpUntil("плашка показана") { box(a).visibility == View.VISIBLE }
        button(a).performClick()
        shadowOf(Looper.getMainLooper()).idle()

        // Диалог у экрана из appcompat, а не из android.app: тамошняя подделка
        // его не видит и молча отдаёт null.
        val dialog = ShadowDialog.getLatestDialog() as? androidx.appcompat.app.AlertDialog
        assertTrue("нажатие сбросило сессию без вопроса", dialog != null && dialog.isShowing)
    }

    @Test
    fun `подтверждение и правда перезапускает сессию`() {
        val a = study()
        pumpUntil("плашка показана") { box(a).visibility == View.VISIBLE }
        paths.clear()
        button(a).performClick()
        shadowOf(Looper.getMainLooper()).idle()
        (ShadowDialog.getLatestDialog() as androidx.appcompat.app.AlertDialog)
            .getButton(android.app.AlertDialog.BUTTON_POSITIVE).performClick()

        pumpUntil("сессия закрыта и набрана заново") {
            paths.any { it.startsWith("DELETE") }
        }
        assertTrue("сессия не закрывалась — кнопка ничего не сделала",
                   paths.any { it.startsWith("DELETE") })
    }

    @Test
    fun `отмена оставляет круг на месте`() {
        val a = study()
        pumpUntil("плашка показана") { box(a).visibility == View.VISIBLE }
        paths.clear()
        button(a).performClick()
        shadowOf(Looper.getMainLooper()).idle()
        (ShadowDialog.getLatestDialog() as androidx.appcompat.app.AlertDialog)
            .getButton(android.app.AlertDialog.BUTTON_NEGATIVE).performClick()
        shadowOf(Looper.getMainLooper()).idle()

        assertTrue("по «Отмена» сессия всё равно сброшена",
                   paths.none { it.startsWith("DELETE") })
    }
}
