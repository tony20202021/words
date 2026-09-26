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
import org.robolectric.annotation.GraphicsMode
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.atomic.AtomicInteger

/**
 * Графики на слабой связи.
 *
 * Жалоба владельца: «в метро совсем плохо, даже с маленьким размером грузится
 * медленно, причём связь есть — то есть условие „сети нет“ не сработает».
 * Семнадцать картинок по 19 КБ на слабом канале — это минуты.
 *
 * Поэтому экран открывается на картинках с прошлого раза, а сеть решает, надо
 * ли их обновлять: версия данных приходит одним коротким запросом. Совпала —
 * не качаем ничего; изменилась — свежие подменяют сохранённые на месте.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class StatsCachedChartsTest {

    private val SUMMARY = """{"words_studied":1,"words_known":1,"words_skipped":0,""" +
        """"words_unknown":0,"total_words":10,"words_for_today":1,""" +
        """"progress_percentage":10.0}"""

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"
    // Имена — из запасного списка приложения: без манифеста (сети нет) экран
    // берёт именно его, и сохранённые картинки должны находиться и тогда.
    private val names = listOf("words_studied", "words_new")
    private val chartRequests = AtomicInteger(0)
    @Volatile private var serverVersion = "v1"
    @Volatile private var chartWidth = 40

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
                val path = request.path ?: ""
                return when {
                    path.contains("chart_manifest") -> MockResponse().setBody(
                        """{"sections":[{"header":"Тест","charts":["words_studied","words_new"],""" +
                            """"type":"monthly_recent"}],"captions":{}}""")
                    path.contains("charts_version") ->
                        MockResponse().setBody("""{"version":"$serverVersion"}""")
                    path.contains("/monthly-chart/") -> {
                        // Считаем только экранные: большие подкачиваются фоном
                        // для увеличения и к скорости открытия отношения не имеют.
                        if (path.contains("res=screen")) chartRequests.incrementAndGet()
                        MockResponse().setBody(Buffer().write(png(chartWidth)))
                    }
                    path.startsWith("/statistics/") -> MockResponse().setBody(SUMMARY)
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

    private fun open(): StatsActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
            .putExtra("language_id", l).putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StatsActivity::class.java, intent).setup().get()
    }

    private fun images(a: StatsActivity): List<ImageView> {
        val out = mutableListOf<ImageView>()
        fun walk(v: View) {
            if (v is ImageView && v.drawable is BitmapDrawable) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(a.findViewById<ViewGroup>(R.id.statsContainer))
        return out
    }

    private fun widths(a: StatsActivity) =
        images(a).map { (it.drawable as BitmapDrawable).bitmap.width }

    private fun allText(a: StatsActivity): String {
        val sb = StringBuilder()
        fun walk(v: View) {
            if (v is android.widget.TextView) sb.append(v.text).append('\n')
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(a.findViewById<ViewGroup>(R.id.statsContainer))
        return sb.toString()
    }

    @Test
    fun the_first_visit_downloads_and_keeps_the_charts() {
        val a = open()
        Screenshots.pumpUntil("картинки загружены") { images(a).size == names.size }

        assertEquals(names.size, chartRequests.get())
        for (name in names) {
            assertTrue("график «$name» не сохранён на диск",
                ChartCache.get(u, l, 2, name) != null || ChartCache.get(u, l, 1, name) != null)
        }
        assertEquals("версия не запомнена", "v1", ChartCache.version(u, l))
    }

    @Test
    fun nothing_is_downloaded_while_the_data_has_not_changed() {
        val first = open()
        Screenshots.pumpUntil("первый заход") { images(first).size == names.size }
        val after = chartRequests.get()

        val second = open()
        Screenshots.pumpUntil("второй заход") { images(second).size == names.size }

        assertEquals("на слабой связи качать было нечего — данные те же",
            after, chartRequests.get())
        assertEquals("показаны сохранённые", listOf(40, 40), widths(second))
    }

    @Test
    fun changed_data_replaces_the_saved_charts() {
        val first = open()
        Screenshots.pumpUntil("первый заход") { images(first).size == names.size }

        serverVersion = "v2"
        chartWidth = 70
        val second = open()
        Screenshots.pumpUntil("свежие подменили сохранённые") { widths(second) == listOf(70, 70) }

        assertEquals("версия обновлена", "v2", ChartCache.version(u, l))
        assertEquals("картинок на экране столько же", names.size, images(second).size)
    }

    @Test
    fun without_network_the_saved_charts_are_shown_and_explained() {
        val first = open()
        Screenshots.pumpUntil("первый заход") { images(first).size == names.size }
        server.shutdown()

        val second = open()
        // Плашка появляется после того, как все попытки скачать свежие
        // провалились, — ждём именно её, а не первую картинку.
        Screenshots.pumpUntil("сохранённые показаны и объяснены") {
            images(second).size == names.size && allText(second).contains("с прошлого раза")
        }
        assertEquals("показаны сохранённые картинки", listOf(40, 40), widths(second))
    }

    @Test
    fun a_half_downloaded_set_does_not_pretend_to_be_current() {
        // Первый заход: одна картинка не пришла. Версию запоминать нельзя —
        // иначе недостающая больше никогда не приедет.
        chartWidth = 40
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    path.contains("chart_manifest") -> MockResponse().setBody(
                        """{"sections":[{"header":"Тест","charts":["words_studied","words_new"],""" +
                            """"type":"monthly_recent"}],"captions":{}}""")
                    path.contains("charts_version") ->
                        MockResponse().setBody("""{"version":"$serverVersion"}""")
                    path.contains("/monthly-chart/words_studied") ->
                        MockResponse().setBody(Buffer().write(png(40)))
                    path.contains("/monthly-chart/") -> MockResponse().setResponseCode(500)
                    path.startsWith("/statistics/") -> MockResponse().setBody(SUMMARY)
                    else -> MockResponse().setResponseCode(404)
                }
            }
        }
        val a = open()
        Screenshots.pumpUntil("одна картинка показана") { images(a).isNotEmpty() }

        assertEquals("версия запомнена при неполном наборе", null, ChartCache.version(u, l))
    }
}
