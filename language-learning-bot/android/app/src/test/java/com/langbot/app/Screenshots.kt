package com.langbot.app

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.TextView
import org.robolectric.Shadows.shadowOf
import java.io.File
import kotlin.math.abs

/**
 * Общая машинерия снимков экрана: отрисовка в PNG, сверка с эталоном и
 * механические проверки вёрстки.
 *
 * Зачем эталоны
 * -------------
 * Картинку, на которую никто не смотрит, можно и не делать. Сверка с эталоном
 * не заменяет человека — она ловит другое: что вёрстка СЪЕХАЛА по сравнению с
 * тем, как было. Содержимое слов для этого заморожено в фикстурах, поэтому
 * любое расхождение пикселей означает изменение оформления, а не словаря.
 *
 * Эталоны лежат в src/test/resources/baseline/ и коммитятся. Когда оформление
 * поменяли НАМЕРЕННО, эталоны переснимаются:
 *
 *     ./gradlew :app:testDebugUnitTest -Pscreenshots.update=true
 *
 * и новые картинки коммитятся вместе с правкой вёрстки — тогда в истории видно,
 * как экран выглядел до и после.
 */
object Screenshots {

    val outDir = File("build/screenshots")
    val baselineDir = File("src/test/resources/baseline")

    /** Пересъёмка эталонов вместо сверки. */
    val updating: Boolean = System.getProperty("screenshots.update") == "true"

    // Допуск. Рендер на одной машине детерминирован, поэтому допуск нужен не
    // ради шума, а чтобы разница в одну-две точки сглаживания не разваливала
    // прогон. Сдвиг блока хотя бы на пиксель затрагивает куда больше площади и
    // всё равно будет пойман.
    private const val CHANNEL_TOLERANCE = 8
    private const val MAX_DIFF_RATIO = 0.001  // 0.1% площади

    fun pumpUntil(what: String, timeoutMs: Long = 15_000, cond: () -> Boolean) {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) return
            Thread.sleep(10)
        }
        throw AssertionError("не дождались: $what")
    }

    /**
     * Колонка внутри ScrollView. ScrollView ищем по типу, а не по индексу:
     * нулевой ребёнок SwipeRefreshLayout — кружок индикатора обновления.
     */
    fun scrollColumnOrRoot(activity: android.app.Activity, swipeId: Int): View {
        val swipe = activity.findViewById<ViewGroup>(swipeId)
            ?: return activity.findViewById(android.R.id.content)
        val scroll = (0 until swipe.childCount).map { swipe.getChildAt(it) }
            .filterIsInstance<ScrollView>().firstOrNull()
            ?: return swipe
        return scroll.getChildAt(0)
    }

    /** Первый ScrollView в дереве — для экранов без SwipeRefreshLayout. */
    fun contentColumn(activity: android.app.Activity): View {
        val root = activity.findViewById<View>(android.R.id.content)
        fun find(v: View): View? {
            if (v is ScrollView && v.childCount > 0) return v.getChildAt(0)
            if (v is ViewGroup) for (i in 0 until v.childCount) find(v.getChildAt(i))?.let { return it }
            return null
        }
        return find(root) ?: root
    }

    /**
     * Ширина экрана из настроек Robolectric (@Config qualifiers), а не число.
     *
     * Раньше здесь стояло 1080, а настроенный экран w411dp-xhdpi — это 822.
     * Снимки выходили шире телефона на треть, и перенос текста в узких колонках
     * на них не воспроизводился: владелец видел на телефоне разорванный номер,
     * а на снимке номер стоял в строку.
     */
    fun screenWidthPx(): Int =
        android.content.res.Resources.getSystem().displayMetrics.widthPixels

    fun render(view: View, widthPx: Int = screenWidthPx()): Bitmap {
        // UNSPECIFIED по высоте: колонка разворачивается на всё содержимое, и в
        // картинку попадает то, что на телефоне видно только прокруткой.
        view.measure(
            View.MeasureSpec.makeMeasureSpec(widthPx, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED),
        )
        view.layout(0, 0, view.measuredWidth, view.measuredHeight)
        val bmp = Bitmap.createBitmap(
            view.measuredWidth.coerceAtLeast(1),
            view.measuredHeight.coerceAtLeast(1),
            Bitmap.Config.ARGB_8888,
        )
        bmp.eraseColor(Color.WHITE)
        view.draw(Canvas(bmp))
        return bmp
    }

    fun write(bmp: Bitmap, file: File) {
        file.parentFile?.mkdirs()
        file.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    /** Доля закрашенных точек. Белый лист — значит рисование не сработало. */
    fun paintedRatio(bmp: Bitmap): Double {
        var painted = 0
        var total = 0
        for (y in 0 until bmp.height step 4) for (x in 0 until bmp.width step 4) {
            total++
            if (bmp.getPixel(x, y) != Color.WHITE) painted++
        }
        return painted.toDouble() / total.coerceAtLeast(1)
    }

    /**
     * Сверка с эталоном. Возвращает описание расхождения или null.
     * В режиме пересъёмки эталон перезаписывается и сверка не делается.
     */
    fun checkBaseline(name: String, bmp: Bitmap): String? {
        val baseline = File(baselineDir, "$name.png")
        if (updating || !baseline.exists()) {
            write(bmp, baseline)
            return if (updating) null
            else "эталона не было, создан: ${baseline.path} — проверьте картинку и закоммитьте"
        }

        val ref = android.graphics.BitmapFactory.decodeFile(baseline.absolutePath)
            ?: return "эталон не читается: ${baseline.path}"
        if (ref.width != bmp.width || ref.height != bmp.height) {
            writeDiffPlaceholder(name, bmp)
            return "размер изменился: было ${ref.width}x${ref.height}, стало ${bmp.width}x${bmp.height}"
        }

        var diff = 0
        val diffBmp = Bitmap.createBitmap(bmp.width, bmp.height, Bitmap.Config.ARGB_8888)
        for (y in 0 until bmp.height) for (x in 0 until bmp.width) {
            val a = ref.getPixel(x, y)
            val b = bmp.getPixel(x, y)
            val far = abs(Color.red(a) - Color.red(b)) > CHANNEL_TOLERANCE ||
                abs(Color.green(a) - Color.green(b)) > CHANNEL_TOLERANCE ||
                abs(Color.blue(a) - Color.blue(b)) > CHANNEL_TOLERANCE
            if (far) {
                diff++
                diffBmp.setPixel(x, y, Color.RED)
            } else {
                // Совпавшее — бледным, чтобы на карте различий было видно, где
                // именно на экране разъехалось.
                val g = (Color.red(b) + Color.green(b) + Color.blue(b)) / 3
                diffBmp.setPixel(x, y, Color.argb(255, 220 + g / 12, 220 + g / 12, 220 + g / 12))
            }
        }
        val ratio = diff.toDouble() / (bmp.width * bmp.height)
        if (ratio <= MAX_DIFF_RATIO) return null

        write(diffBmp, File(outDir, "diff_$name.png"))
        write(bmp, File(outDir, "actual_$name.png"))
        return "оформление разъехалось на %.2f%% площади — см. build/screenshots/diff_%s.png; ".format(ratio * 100, name) +
            "если правка вёрстки намеренная, пересними эталоны: ./gradlew :app:testDebugUnitTest -Pscreenshots.update=true"
    }

    private fun writeDiffPlaceholder(name: String, bmp: Bitmap) = write(bmp, File(outDir, "actual_$name.png"))

    /** Механические дефекты вёрстки, видимые без человека. */
    fun layoutProblems(root: View, rootWidth: Int): List<String> {
        val problems = mutableListOf<String>()
        fun walk(v: View) {
            // За скрытый узел заходить нечего: его детей не измеряют, и у них
            // законно нулевой размер. Обходчик этого не знал и ругался на
            // кнопку внутри спрятанной плашки — видимую саму по себе, но не
            // существующую на экране.
            if (v.visibility != View.VISIBLE) return
            if (v is TextView && v.text.isNotEmpty()) {
                val label = v.text.toString().take(30).replace("\n", " ")
                v.layout?.let { lay ->
                    for (line in 0 until lay.lineCount) {
                        if (lay.getEllipsisCount(line) > 0) {
                            problems += "обрезан текст «$label…»"
                            break
                        }
                    }
                }
                if (v.width == 0 || v.height == 0) {
                    problems += "нулевой размер у непустого текста «$label»"
                }
            }
            val loc = IntArray(2)
            v.getLocationInWindow(loc)
            if (v.width > 0 && loc[0] + v.width > rootWidth + 1) {
                val what = (v as? TextView)?.text?.toString()?.take(30) ?: v.javaClass.simpleName
                problems += "выходит за правый край: «$what» (до ${loc[0] + v.width} при ширине $rootWidth)"
            }
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return problems.distinct()
    }

    /** Все TextView дерева — основа структурных утверждений. */
    fun texts(root: View): List<TextView> {
        val out = mutableListOf<TextView>()
        fun walk(v: View) {
            if (v.visibility != View.VISIBLE) return   // то же: скрытое — не на экране
            if (v is TextView && v.text.isNotEmpty()) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return out
    }
}
