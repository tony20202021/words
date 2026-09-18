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
import java.io.ByteArrayOutputStream
import java.util.concurrent.atomic.AtomicInteger

/**
 * Картинки статистики грузятся разом и встают в порядке манифеста.
 *
 * Прежде 17 картинок шли строго по очереди, и на слабом мобильном время
 * складывалось. Здесь сервер нарочно отдаёт первую картинку последней:
 * параллельная загрузка не должна перемешать порядок на экране.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class StatsParallelLoadTest {

    private lateinit var server: MockWebServer
    private val inFlight = AtomicInteger(0)
    private val maxInFlight = AtomicInteger(0)

    // Ширина картинки — её «имя»: по ней видно, в каком порядке они встали.
    private val widths = mapOf("a" to 10, "b" to 20, "c" to 30, "d" to 40)
    // Первая отвечает последней.
    private val delaysMs = mapOf("a" to 600L, "b" to 300L, "c" to 150L, "d" to 0L)

    private fun png(width: Int): ByteArray {
        val bmp = Bitmap.createBitmap(width, 8, Bitmap.Config.ARGB_8888)
        val out = ByteArrayOutputStream()
        bmp.compress(Bitmap.CompressFormat.PNG, 100, out)
        return out.toByteArray()
    }

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        val images = widths.mapValues { png(it.value) }
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    path.contains("chart_manifest") -> MockResponse().setBody(
                        """{"sections":[{"header":"Тест","charts":["a","b","c","d"],""" +
                            """"type":"monthly_recent"}],"captions":{}}""")
                    path.contains("/monthly-chart/") -> {
                        val name = path.substringAfter("/monthly-chart/").substringBefore("?")
                        val now = inFlight.incrementAndGet()
                        maxInFlight.accumulateAndGet(now) { a, b -> maxOf(a, b) }
                        Thread.sleep(delaysMs.getValue(name))
                        inFlight.decrementAndGet()
                        MockResponse().setBody(Buffer().write(images.getValue(name)))
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

    private fun images(root: View): List<ImageView> {
        val out = mutableListOf<ImageView>()
        fun walk(v: View) {
            if (v is ImageView && v.drawable is BitmapDrawable) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return out
    }

    @Test
    fun charts_load_together_and_keep_manifest_order() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val activity = Robolectric.buildActivity(StatsActivity::class.java, intent).setup().get()
        val container = activity.findViewById<ViewGroup>(R.id.statsContainer)

        Screenshots.pumpUntil("все картинки загружены") { images(container).size == 4 }

        val shown = images(container).map { (it.drawable as BitmapDrawable).bitmap.width }
        assertEquals("порядок на экране — как в манифесте", listOf(10, 20, 30, 40), shown)
        assertTrue("картинки грузились по одной (одновременно: ${maxInFlight.get()})",
            maxInFlight.get() > 1)
    }
}
