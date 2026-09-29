package com.langbot.app

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.drawable.BitmapDrawable
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.ChartCache
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import okio.Buffer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.android.controller.ActivityController
import org.robolectric.annotation.GraphicsMode
import java.io.ByteArrayOutputStream
import java.io.File

/**
 * Экран статистики без сети: не падать и оживать, когда сеть вернулась.
 *
 * Жалоба владельца: «при отключённой сети на статистике часто приложение просто
 * вылетает — сегодня утром было много раз; либо рисует экран, что сети нет, и
 * больше ничего не обновляет, даже когда сеть восстанавливается».
 *
 * По журналам сервера за то утро до него дошло ровно одно открытие статистики,
 * и оно прошло успешно. Значит, падало там, где до сервера не доходило вовсе.
 *
 * Без сети каждая попытка живёт долго (семнадцать запросов ждут таймаута), и
 * обновление, начатое поверх незаконченного, рисовало в тот же контейнер:
 * второй заход добавлял картинку, у которой уже есть родитель, — Android на
 * этом падает.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class StatsOfflineRecoveryTest {

    private val u = "user-1"
    private val l = "lang-1"
    private lateinit var server: MockWebServer
    @Volatile private var offline = true

    private val summary = """{"words_studied":1,"words_known":1,"words_skipped":0,""" +
        """"words_unknown":0,"total_words":10,"words_for_today":1,""" +
        """"progress_percentage":10.0}"""

    private fun png(width: Int): ByteArray {
        val out = ByteArrayOutputStream()
        Bitmap.createBitmap(width, 8, Bitmap.Config.ARGB_8888)
            .compress(Bitmap.CompressFormat.PNG, 100, out)
        return out.toByteArray()
    }

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ChartCache.init(ctx)
        File(ctx.filesDir, "charts").deleteRecursively()
        UserPrefs.saveUserId(ctx, u)
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                if (offline) return MockResponse().setResponseCode(503)
                val path = request.path ?: ""
                return when {
                    path.contains("chart_manifest") -> MockResponse().setBody(
                        """{"sections":[{"header":"Тест","charts":["words_studied","words_new"],""" +
                            """"type":"monthly_recent"}],"captions":{}}""")
                    path.contains("charts_version") -> MockResponse().setBody("""{"version":"v1"}""")
                    path.contains("-chart/") -> MockResponse().setBody(Buffer().write(png(40)))
                    path.startsWith("/statistics/") -> MockResponse().setBody(summary)
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

    private fun controller(): ActivityController<StatsActivity> {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
            .putExtra("language_id", l).putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StatsActivity::class.java, intent).setup()
    }

    private fun container(a: StatsActivity): ViewGroup = a.findViewById(R.id.statsContainer)

    private fun images(a: StatsActivity): List<ImageView> {
        val out = mutableListOf<ImageView>()
        fun walk(v: View) {
            if (v is ImageView && v.drawable is BitmapDrawable) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(container(a))
        return out
    }

    private fun texts(a: StatsActivity): String {
        val sb = StringBuilder()
        fun walk(v: View) {
            if (v is android.widget.TextView) sb.append(v.text).append('\n')
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(container(a))
        return sb.toString()
    }

    private fun warmCache() {
        offline = false
        val warm = controller()
        Screenshots.pumpUntil("кеш графиков заполнен") { images(warm.get()).size == 2 }
        warm.pause().stop().destroy()
        offline = true
    }

    @Test
    fun saved_charts_appear_without_waiting_for_the_slow_summary() {
        """
        Случай владельца: «в метро на статистике отрисовался пустой экран с
        крутяшкой, хотя до этого графики смотрел». Связь есть, но медленная:
        сводка не падает, а тянется, — и графики ждали её, вместо того чтобы
        показать сохранённые.
        """
        warmCache()
        offline = false
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    // Сводка «думает» дольше, чем человек готов ждать.
                    path.matches(Regex("/statistics/[^/]+/[^/]+")) ->
                        MockResponse().setBody(summary).setBodyDelay(30, java.util.concurrent.TimeUnit.SECONDS)
                    path.contains("chart_manifest") -> MockResponse().setBody(
                        """{"sections":[{"header":"Тест","charts":["words_studied","words_new"],""" +
                            """"type":"monthly_recent"}],"captions":{}}""")
                    path.contains("charts_version") ->
                        MockResponse().setBody("""{"version":"v1"}""").setBodyDelay(30, java.util.concurrent.TimeUnit.SECONDS)
                    else -> MockResponse().setResponseCode(503)
                }
            }
        }
        val a = controller().get()
        Screenshots.pumpUntil("сохранённые графики показаны, не дожидаясь чисел") {
            images(a).size == 2
        }
        assertEquals("экран остался пустым, пока тянулась сводка", 2, images(a).size)
    }

    @Test
    fun refreshing_again_while_the_first_attempt_is_still_running_does_not_crash() {
        warmCache()
        val c = controller()
        val a = c.get()
        // Обновление поверх незаконченного — именно так и получалось у владельца:
        // без сети первая попытка тянется долго, и он дёргал экран ещё раз.
        a.findViewById<androidx.swiperefreshlayout.widget.SwipeRefreshLayout>(R.id.swipeRefresh)
            .let { it.isRefreshing = true }
        a.refreshForTest()
        a.refreshForTest()
        runCatching {
            Screenshots.pumpUntil("экран устоял") {
                images(a).size == 2 && texts(a).contains("с прошлого раза")
            }
        }
        assertEquals("на экране не две сохранённые картинки (текст: ${texts(a)})",
            2, images(a).size)
    }

    @Test
    fun the_screen_comes_back_by_itself_when_the_network_returns() {
        val c = controller()
        val a = c.get()
        Screenshots.pumpUntil("сначала сказано, что связи нет") { texts(a).contains("Нет связи") }

        offline = false
        // Возвращение на экран — самый частый способ: человек ушёл и вернулся.
        c.pause().resume()

        Screenshots.pumpUntil("экран ожил сам") { images(a).size == 2 }
        assertTrue("плашка «нет связи» осталась: ${texts(a)}",
            !texts(a).contains("Не удалось загрузить статистику"))
    }

    @Test
    fun pulling_to_refresh_does_not_add_a_second_spinner() {
        """Случай владельца: «потянул экран вниз — стало 2 крутяшки»."""
        offline = false
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    path.contains("chart_manifest") -> MockResponse().setBody(
                        """{"sections":[{"header":"Тест","charts":["words_studied","words_new"],""" +
                            """"type":"monthly_recent"}],"captions":{}}""")
                    // Всё остальное тянется — экран остаётся в ожидании.
                    else -> MockResponse().setBody("{}")
                        .setBodyDelay(30, java.util.concurrent.TimeUnit.SECONDS)
                }
            }
        }
        val a = controller().get()
        Screenshots.pumpUntil("ожидание показано") { spinners(a).isNotEmpty() }
        val before = spinners(a).size
        a.refreshForTest()
        a.refreshForTest()
        Screenshots.pumpUntil("экран пересобран") { spinners(a).isNotEmpty() }

        assertEquals("крутяшки накопились", before, spinners(a).size)
    }

    private fun spinners(a: StatsActivity): List<View> {
        val out = mutableListOf<View>()
        fun walk(v: View) {
            if (v is android.widget.ProgressBar) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(container(a))
        return out
    }

    @Test
    fun a_successful_refresh_does_not_stack_a_second_copy_of_the_charts() {
        offline = false
        val c = controller()
        val a = c.get()
        Screenshots.pumpUntil("первый показ") { images(a).size == 2 }

        a.refreshForTest()
        Screenshots.pumpUntil("второй показ") { images(a).size == 2 }
        assertEquals("после обновления графиков стало больше", 2, images(a).size)
    }

    @Test
    fun without_network_and_without_saved_charts_the_screen_explains_itself() {
        val c = controller()
        val a = c.get()
        Screenshots.pumpUntil("объяснение показано") { texts(a).contains("Нет связи") }
        assertEquals("рисовать было нечего, а картинки появились", 0, images(a).size)
    }
}
