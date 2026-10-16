package com.langbot.app

import android.content.Intent
import android.view.View
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.network.NetworkRetry
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
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.shadows.ShadowLooper
import java.util.concurrent.TimeUnit

/**
 * Пока ждём первый ответ сервера, экран обязан сказать, что он ждёт.
 *
 * Жалоба владельца: «ожидание сети — до первого сообщения, что ждём таймаут,
 * непонятно: ждём или зависло. Надо какую-то крутяшку или такое же сообщение
 * про первый таймаут».
 *
 * Тонкость в том, что на каждое нажатие мигать плашкой нельзя: живой сервер
 * отвечает за десятки миллисекунд, и надпись «соединяемся» успевала бы только
 * дёрнуться. Поэтому она отложена на полсекунды — и в быстром случае не
 * появляется вовсе.
 */
@RunWith(RobolectricTestRunner::class)
class WaitingNoticeTest {

    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest) = MockResponse().setResponseCode(404)
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    private fun study(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        // Загрузка сессии в этих проверках заведомо проваливается (сервер
        // отвечает 404), и на своём пути она гасит плашку связи. Дожидаемся,
        // пока это отыграет, иначе проверка меряет не то, что ставит.
        ShadowLooper.idleMainLooper(30, TimeUnit.SECONDS)
        return a
    }

    // Плашка связи своя и лежит поверх карточки: встроенная в столбец, она
    // сдвигала содержимое вниз, и это читалось как переход к следующему слову.
    private fun notice(a: StudyActivity): TextView = a.findViewById(R.id.tvConnection)

    private fun firstAttempt() = NetworkRetry.Status(
        attempt = 1, total = 3, timeoutMs = 2000, lastError = null)

    private fun secondAttempt() = NetworkRetry.Status(
        attempt = 2, total = 3, timeoutMs = 6000, lastError = "timeout")

    @Test
    fun a_quick_answer_leaves_the_screen_quiet() {
        val a = study()
        a.showWaitingForTest(firstAttempt())
        // Сервер ответил сразу — надпись не должна успеть появиться.
        a.clearWaitingForTest()
        ShadowLooper.idleMainLooper(2, TimeUnit.SECONDS)
        assertEquals("плашка мигнула на обычном быстром ответе",
                     View.GONE, notice(a).visibility)
    }

    @Test
    fun a_slow_first_attempt_says_that_we_are_waiting() {
        val a = study()
        a.showWaitingForTest(firstAttempt())
        ShadowLooper.idleMainLooper(StudyActivity.FIRST_WAIT_NOTICE_MS + 50,
                                    TimeUnit.MILLISECONDS)
        assertEquals("экран промолчал, пока шла первая попытка",
                     View.VISIBLE, notice(a).visibility)
        val text = notice(a).text.toString()
        assertTrue("по надписи не понять, что идёт ожидание: «$text»",
                   text.contains("Соединяемся"))
        assertTrue("нечему крутиться: в надписи нет значка ожидания: «$text»",
                   text.contains("⏳"))
    }

    @Test
    fun the_notice_does_not_appear_before_half_a_second() {
        val a = study()
        a.showWaitingForTest(firstAttempt())
        ShadowLooper.idleMainLooper(StudyActivity.FIRST_WAIT_NOTICE_MS - 100,
                                    TimeUnit.MILLISECONDS)
        assertEquals("плашка выскочила раньше времени",
                     View.GONE, notice(a).visibility)
    }

    @Test
    fun the_second_attempt_speaks_at_once() {
        """Вторая попытка означает, что первая уже не ответила, — тянуть нечего."""
        val a = study()
        a.showWaitingForTest(secondAttempt())
        assertEquals(View.VISIBLE, notice(a).visibility)
        val text = notice(a).text.toString()
        assertTrue("не сказано, какая это попытка: «$text»", text.contains("Попытка 2 из 3"))
        assertFalse("на второй попытке значок ожидания лишний: «$text»", text.contains("⏳"))
    }

    @Test
    fun a_pending_notice_is_cancelled_when_the_answer_arrives() {
        """Ответ пришёл до полсекунды — отложенная надпись обязана отмениться."""
        val a = study()
        a.showWaitingForTest(firstAttempt())
        ShadowLooper.idleMainLooper(StudyActivity.FIRST_WAIT_NOTICE_MS - 100,
                                    TimeUnit.MILLISECONDS)
        a.clearWaitingForTest()
        ShadowLooper.idleMainLooper(5, TimeUnit.SECONDS)
        assertEquals("надпись всплыла уже после ответа сервера",
                     View.GONE, notice(a).visibility)
    }
}

/**
 * Плашка связи не должна двигать карточку.
 *
 * Жалоба владельца: «окно соединения выдаётся как часть экрана и сдвигает всё
 * остальное вниз; если смотреть на нижнюю часть — выглядит как смена экрана на
 * следующий, и приходится долго пересматривать, чтобы понять, что ничего не
 * изменилось».
 */
@RunWith(RobolectricTestRunner::class)
class ConnectionNoticeDoesNotShiftTheCardTest {

    private fun study(): StudyActivity {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        val intent = Intent(ctx, StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
    }

    @Test
    fun `плашка лежит поверх карточки, а не в её столбце`() {
        val a = study()
        val notice = a.findViewById<TextView>(R.id.tvConnection)
        val column = a.findViewById<android.view.View>(R.id.cardScrollContent)
        val swipe = a.findViewById<android.view.View>(R.id.swipeRefresh)

        // Не внутри прокручиваемого столбца — иначе она его и сдвигает.
        var p = notice.parent
        val parents = mutableListOf<Any?>()
        while (p != null) { parents.add(p); p = (p as? android.view.View)?.parent }
        org.junit.Assert.assertFalse(
            "плашка внутри столбца карточки — она будет двигать содержимое",
            parents.contains(column))
        org.junit.Assert.assertFalse(
            "плашка внутри области прокрутки", parents.contains(swipe))
        // И лежит выше по стопке: у неё есть подъём над остальным.
        org.junit.Assert.assertTrue("плашка не поднята над карточкой",
            notice.elevation > 0f)
    }

    @Test
    fun `появление плашки не меняет положение карточки`() {
        val a = study()
        val notice = a.findViewById<TextView>(R.id.tvConnection)
        val swipe = a.findViewById<android.view.View>(R.id.swipeRefresh)
        val before = swipe.top

        a.showWaitingForTest(NetworkRetry.Status(
            attempt = 2, total = 2, timeoutMs = 6000, lastError = "timeout"))
        org.robolectric.shadows.ShadowLooper.idleMainLooper()

        org.junit.Assert.assertEquals(View.VISIBLE, notice.visibility)
        org.junit.Assert.assertEquals(
            "карточка уехала вниз от плашки связи", before, swipe.top)
    }
}
