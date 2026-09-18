package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
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

/**
 * Экран «слова кончились» — отдельное состояние, без хвостов прошлой карточки.
 *
 * Владелец дважды за утро видел странный экран: под «На сегодня всё повторено!»
 * висела плашка «✓ Правильно!» от последнего ответа в режиме выбора, а в другой
 * раз — голый разделитель над пустотой. Функция прятала лишь то, что вспомнили.
 */
@RunWith(RobolectricTestRunner::class)
class CompletionScreenTest {

    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    path.endsWith("/bundle") -> MockResponse().setResponseCode(404)
                    path.startsWith("/session/") ->
                        MockResponse().setResponseCode(200).setBody("""{"session_id":"sid-1","card":null}""")
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

    private fun doneScreen(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val activity = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        Screenshots.pumpUntil("экран завершения отрисован") {
            activity.findViewById<ViewGroup>(R.id.cardContent).childCount > 0
        }
        return activity
    }

    // Screenshots.texts отдаёт сами TextView, а не строки. Склейка без
    // преобразования давала их служебное представление, и проверка
    // «офлайн не пишет „всё повторено“» проходила впустую, не видя ни строки.
    private fun texts(activity: StudyActivity): String =
        Screenshots.texts(activity.findViewById(android.R.id.content))
            .joinToString(" | ") { it.text.toString() }

    @Test
    fun leftovers_of_the_last_card_are_hidden() {
        val activity = doneScreen()
        // Хвосты последней карточки — ровно то, что было на снимке владельца.
        activity.findViewById<TextView>(R.id.tvPickResult).apply {
            text = "✓  Правильно!"; visibility = View.VISIBLE
        }
        activity.findViewById<View>(R.id.banButtonRow).visibility = View.VISIBLE
        activity.findViewById<View>(R.id.divider).visibility = View.VISIBLE

        activity.showAllDone()

        assertEquals("плашка результата прошлого ответа",
            View.GONE, activity.findViewById<View>(R.id.tvPickResult).visibility)
        assertEquals("ряд «запретить пару»",
            View.GONE, activity.findViewById<View>(R.id.banButtonRow).visibility)
        assertEquals("разделитель над пустотой",
            View.GONE, activity.findViewById<View>(R.id.divider).visibility)
        assertTrue(texts(activity).contains("На сегодня всё повторено!"))
    }

    @Test
    fun offline_completion_does_not_claim_the_day_is_done() {
        // Без сети «на сегодня всё» знать нельзя — кончилась лишь скачанная партия.
        val activity = doneScreen()
        activity.showAllDone(offline = true)
        val shown = texts(activity)
        assertFalse("офлайн не может знать, что на сегодня всё: $shown",
            shown.contains("всё повторено"))
        assertTrue(shown.contains("Офлайн-партия пройдена"))
    }
}
