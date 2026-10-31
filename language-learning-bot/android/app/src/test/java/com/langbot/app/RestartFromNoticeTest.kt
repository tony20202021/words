package com.langbot.app

import android.content.Intent
import android.os.Looper
import android.view.View
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
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
    private fun notice(a: StudyActivity): TextView = a.findViewById(R.id.tvRestartNotice)
    /** Запасная ссылка отдельной строкой — должна молчать, пока слова нашлись. */
    private fun fallback(a: StudyActivity): TextView = a.findViewById(R.id.linkRestartNow)

    /** Нажатие по самому слову в тексте плашки. */
    private fun linkSpans(a: StudyActivity): List<android.text.style.ClickableSpan> {
        val text = notice(a).text
        if (text !is android.text.Spanned) return emptyList()
        return text.getSpans(0, text.length, android.text.style.ClickableSpan::class.java).toList()
    }

    private fun clickLink(a: StudyActivity) {
        val span = linkSpans(a).firstOrNull() ?: fail("в тексте плашки нет ссылки").let { return }
        span.onClick(notice(a))
    }

    /** Какие слова сделаны ссылкой. */
    private fun linkedPhrase(a: StudyActivity): String? {
        val text = notice(a).text
        if (text !is android.text.Spanned) return null
        val span = linkSpans(a).firstOrNull() ?: return null
        return text.subSequence(text.getSpanStart(span), text.getSpanEnd(span)).toString()
    }

    @Test
    fun `ссылкой сделаны сами слова о перезапуске`() {
        """
        Жалоба владельца: «сделать не отдельной строкой, а прямо в тексте, на
        словах о рекомендации перезапуска».
        """
        val a = study()
        pumpUntil("плашка показана") { box(a).visibility == View.VISIBLE }
        assertEquals("ссылкой сделаны не те слова",
                     "перезапустить сессию", linkedPhrase(a))
        assertEquals("запасная строка показана, хотя слова нашлись",
                     View.GONE, fallback(a).visibility)
    }

    @Test
    fun `без нужных слов остаётся запасная ссылка строкой`() {
        """
        Текст приходит с сервера. Если слов в нём нет (сервер старее или текст
        переписали), ход к действию теряться не должен.
        """
        notice = "⚠️ Ошибок слишком много."
        val a = study()
        pumpUntil("плашка показана") { box(a).visibility == View.VISIBLE }
        assertTrue("ссылка повисла на чужих словах", linkSpans(a).isEmpty())
        assertEquals("запасной ссылки нет — действие стало недостижимо",
                     View.VISIBLE, fallback(a).visibility)
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
        clickLink(a)
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
        clickLink(a)
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
        clickLink(a)
        shadowOf(Looper.getMainLooper()).idle()
        (ShadowDialog.getLatestDialog() as androidx.appcompat.app.AlertDialog)
            .getButton(android.app.AlertDialog.BUTTON_NEGATIVE).performClick()
        shadowOf(Looper.getMainLooper()).idle()

        assertTrue("по «Отмена» сессия всё равно сброшена",
                   paths.none { it.startsWith("DELETE") })
    }
}
