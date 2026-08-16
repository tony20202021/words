package com.langbot.app

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.content.Intent
import android.os.Looper
import android.view.View
import androidx.test.core.app.ApplicationProvider
import com.google.gson.Gson
import com.langbot.app.network.BLSClient
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardItem
import com.langbot.app.network.CardMeta
import com.langbot.app.network.ExtraContentItem
import com.langbot.app.network.ExtraRow
import com.langbot.app.network.SessionResponse
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * Снимок экрана карточки в PNG — без эмулятора и телефона.
 *
 * Зачем
 * -----
 * Больше половины дефектов этой недели были из разряда «на экране не так»:
 * блок доп. информации уезжал вправо, счётчики не двигались, кнопка стояла не
 * там. Ни один из них не ловился тестами, и каждый находил владелец, глядя на
 * телефон. Проверить это чтением кода нельзя — я дважды писал «починено», не
 * увидев экрана, и дважды ошибался.
 *
 * Robolectric 4.11 умеет рисовать по-настоящему (GraphicsMode.NATIVE), поэтому
 * View можно измерить, разложить и вывести в Bitmap. Получается картинка, на
 * которую можно посмотреть — не замена живому телефону, но ловит именно то, что
 * не ловится структурными проверками: наложения, обрезку, уехавшее выравнивание.
 *
 * Файлы кладутся в app/build/screenshots/ — это каталог сборки, в репозиторий
 * не попадает.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w411dp-h891dp-xhdpi")
class ScreenshotTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"
    private val gson = Gson()

    private val outDir = File("build/screenshots")

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, u)
        outDir.mkdirs()

        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return if (path.startsWith("/session/") && request.method == "GET") {
                    MockResponse().setResponseCode(200)
                        .setBody(gson.toJson(SessionResponse(session_id = "sid-1", card = hebrewCard())))
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

    /** Ответная сторона ивритского слова с блоками огласовок и однокоренных. */
    private fun hebrewCard() = Card(
        show_answer = true,
        content = listOf(
            CardItem("foreign", "עִם"),
            CardItem("transcription", "/ʔim/\nим"),
            CardItem("translation", "с, вместе с"),
            CardItem("label", "📚 предлог"),
        ),
        buttons = listOf(
            CardButton("rate", "➡️ Дальше", "success", "dont_know", "submit", "dont_know"),
            CardButton("toggle_skip", "⏩ Пропускать", "outline-secondary", null, "submit", "skip"),
        ),
        meta = CardMeta(
            word_id = "w1", word_number = 15, session_pos = 3, session_total = 10,
            correct_count = 2, incorrect_count = 1,
            result_history = listOf("know", "know", "dont_know"),
            pending_result = null, score_badge = null, words_for_today = 10,
        ),
        extra_content = listOf(
            ExtraContentItem("label", "🔤 То же написание с другой огласовкой:", "tones"),
            ExtraContentItem(
                "extra", "запасной текст", "tones",
                header = "<b>עם</b>: <i>вариантов огласовки: 2</i>",
                header_foreign = "<b>עם</b>", header_ru = "вариантов огласовки: 2",
                rows = listOf(
                    ExtraRow("", "עִם [ʔim]", "с, вместе с"),
                    ExtraRow("", "עַם [ʔam]", "народ"),
                ),
            ),
            ExtraContentItem("label", "🌱 Слова с той же основой:", "references"),
            ExtraContentItem(
                "extra", "запасной текст", "references",
                header = "<b>עם</b>: <i>слов с этой основой: 3</i>",
                header_foreign = "<b>עם</b>", header_ru = "слов с этой основой: 3",
                rows = listOf(
                    ExtraRow("[#27]", "אוֹתוֹ [ʔoˈto]", "его; тот самый"),
                    ExtraRow("[#33]", "אוֹתִי [ʔoˈti]", "меня"),
                ),
            ),
        ),
    )

    private fun pumpUntil(what: String, timeoutMs: Long = 15_000, cond: () -> Boolean) {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) return
            Thread.sleep(10)
        }
        throw AssertionError("не дождались: $what")
    }

    /**
     * Колонка внутри ScrollView — у неё нет id, добираемся по дереву.
     * Снимать сам ScrollView бесполезно: он отдаст только видимый кусок, а
     * блоки огласовок живут ниже сгиба — то есть ровно то, что нужно увидеть.
     */
    private fun scrollColumn(activity: StudyActivity): View {
        val swipe = activity.findViewById<android.view.ViewGroup>(R.id.swipeRefresh)
        // Ищем по типу, а не по индексу: нулевой ребёнок SwipeRefreshLayout —
        // это кружок индикатора обновления, ScrollView идёт после него.
        val scroll = (0 until swipe.childCount).map { swipe.getChildAt(it) }
            .filterIsInstance<android.widget.ScrollView>()
            .firstOrNull() ?: throw AssertionError("в swipeRefresh нет ScrollView")
        return scroll.getChildAt(0)
    }

    /** Снять вид в PNG. Возвращает долю незакрашенных фоном пикселей — мера «что-то нарисовано». */
    private fun capture(view: View, name: String): Double {
        // Высота UNSPECIFIED: колонка разворачивается на всё содержимое, и в
        // картинку попадает то, что на телефоне видно только прокруткой.
        view.measure(
            View.MeasureSpec.makeMeasureSpec(1080, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED),
        )
        view.layout(0, 0, view.measuredWidth, view.measuredHeight)
        val w = view.measuredWidth.coerceAtLeast(1)
        val h = view.measuredHeight.coerceAtLeast(1)
        val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        bitmap.eraseColor(Color.WHITE)
        view.draw(Canvas(bitmap))

        val file = File(outDir, "$name.png")
        file.outputStream().use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }

        // Доля пикселей, отличных от фона: пустой экран означает, что рисование
        // не сработало, и молчать об этом нельзя — картинка тогда бесполезна.
        var painted = 0
        val step = 4
        var total = 0
        for (y in 0 until h step step) {
            for (x in 0 until w step step) {
                total++
                if (bitmap.getPixel(x, y) != Color.WHITE) painted++
            }
        }
        println("снимок: ${file.absolutePath} (${w}x$h, закрашено ${painted * 100 / total}%)")
        return painted.toDouble() / total
    }

    @Test
    fun hebrew_answer_card_is_rendered_to_a_png() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", l)
            .putExtra("language_name", "Иврит")
        val activity = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()

        // Ждём именно содержимое, а не «активность существует»: первая версия
        // этой проверки была всегда истинной и сняла голый заголовок.
        pumpUntil("карточка и блоки доп. информации отрисованы") {
            activity.findViewById<android.view.ViewGroup>(R.id.cardContent).childCount > 0 &&
                activity.findViewById<android.view.ViewGroup>(R.id.extraCardsArea).childCount > 0
        }

        val painted = capture(scrollColumn(activity), "hebrew_answer_card")
        assertTrue("экран пустой — рисование не сработало, картинка бесполезна", painted > 0.01)
    }
}
