package com.langbot.app

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.drawable.BitmapDrawable
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
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
import org.robolectric.android.controller.ActivityController
import java.io.ByteArrayOutputStream
import java.util.Collections
import java.util.concurrent.atomic.AtomicInteger

/**
 * Два варианта картинок статистики на андроиде.
 *
 * Требования владельца: лёгкие — сразу, чтобы заполнить экран; большие — фоном,
 * не блокируя; при уходе с экрана подкачку прекращать. Плюс увеличение по
 * нажатию, которого в приложении не было вовсе.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class StatsZoomTest {

    private lateinit var server: MockWebServer
    private val names = listOf("a", "b", "c", "d")
    private val screenServed = AtomicInteger(0)
    private val zoomArrived = AtomicInteger(0)
    private val zoomInFlight = AtomicInteger(0)
    private val zoomMaxInFlight = AtomicInteger(0)
    private val screenWhenFirstZoom = AtomicInteger(-1)
    @Volatile private var zoomDelayMs = 200L
    private val zoomPaths = Collections.synchronizedList(mutableListOf<String>())

    private fun png(width: Int): ByteArray {
        val out = ByteArrayOutputStream()
        Bitmap.createBitmap(width, 8, Bitmap.Config.ARGB_8888).compress(Bitmap.CompressFormat.PNG, 100, out)
        return out.toByteArray()
    }

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        val screenPng = png(10)
        val zoomPng = png(50)
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    path.contains("chart_manifest") -> MockResponse().setBody(
                        """{"sections":[{"header":"Тест","charts":["a","b","c","d"],""" +
                            """"type":"monthly_recent"}],"captions":{}}""")
                    path.contains("/monthly-chart/") && path.contains("res=zoom") -> {
                        if (zoomArrived.incrementAndGet() == 1) screenWhenFirstZoom.set(screenServed.get())
                        zoomPaths += path
                        val now = zoomInFlight.incrementAndGet()
                        zoomMaxInFlight.accumulateAndGet(now) { a, b -> maxOf(a, b) }
                        Thread.sleep(zoomDelayMs)
                        zoomInFlight.decrementAndGet()
                        MockResponse().setBody(Buffer().write(zoomPng))
                    }
                    path.contains("/monthly-chart/") -> {
                        screenServed.incrementAndGet()
                        MockResponse().setBody(Buffer().write(screenPng))
                    }
                    path.startsWith("/statistics/") -> MockResponse().setBody(
                        """{"words_studied":1,"words_known":1,"words_skipped":0,""" +
                            """"words_unknown":0,"total_words":10,"words_for_today":1,""" +
                            """"progress_percentage":10.0}""")
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

    private fun open(): ActivityController<StatsActivity> {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StatsActivity::class.java, intent).setup()
    }

    private fun charts(root: View): List<ImageView> {
        val out = mutableListOf<ImageView>()
        fun walk(v: View) {
            if (v is ImageView && v.drawable is BitmapDrawable) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return out
    }

    @Test
    fun big_pictures_follow_the_light_ones_two_at_a_time() {
        val activity = open().get()
        val container = activity.findViewById<ViewGroup>(R.id.statsContainer)
        Screenshots.pumpUntil("лёгкие картинки на экране") { charts(container).size == 4 }
        Screenshots.pumpUntil("большие подкачаны") { zoomArrived.get() == 4 && zoomInFlight.get() == 0 }

        assertEquals("большие пошли раньше, чем пришли все лёгкие", 4, screenWhenFirstZoom.get())
        assertTrue("больших разом больше двух: ${zoomMaxInFlight.get()}", zoomMaxInFlight.get() <= 2)
        assertEquals("каждая большая — ровно раз", names.size, zoomPaths.map {
            it.substringAfter("/monthly-chart/").substringBefore("?") }.toSet().size)
    }

    @Test
    fun leaving_the_screen_stops_the_prefetch() {
        zoomDelayMs = 700L
        val controller = open()
        val activity = controller.get()
        val container = activity.findViewById<ViewGroup>(R.id.statsContainer)
        Screenshots.pumpUntil("лёгкие картинки на экране") { charts(container).size == 4 }
        Screenshots.pumpUntil("подкачка началась") { zoomArrived.get() >= 1 }
        controller.pause().stop()
        Thread.sleep(2500)

        assertTrue("подкачка не отменена", activity.zoomPrefetchJob?.isCancelled == true)
        assertTrue("после ухода продолжили качать: ${zoomArrived.get()} из 4",
            zoomArrived.get() <= 2)
    }

    @Test
    fun tapping_a_chart_opens_it_full_screen_for_zooming() {
        val activity = open().get()
        val container = activity.findViewById<ViewGroup>(R.id.statsContainer)
        Screenshots.pumpUntil("лёгкие картинки на экране") { charts(container).size == 4 }

        charts(container).first().performClick()

        val dialog = activity.zoomDialog
        assertTrue("увеличение не открылось", dialog?.isShowing == true)
        val zoom = dialog!!.window!!.decorView.let { root ->
            val found = mutableListOf<ZoomImageView>()
            fun walk(v: View) {
                if (v is ZoomImageView) found += v
                if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
            }
            walk(root); found.firstOrNull()
        }
        assertTrue("в полноэкранном окне нет увеличиваемой картинки", zoom != null)
        Screenshots.pumpUntil("подменилась на большую") {
            ((zoom!!.drawable as? BitmapDrawable)?.bitmap?.width ?: 0) == 50
        }
    }
}
