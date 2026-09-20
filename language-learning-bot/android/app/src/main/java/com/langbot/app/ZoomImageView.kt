package com.langbot.app

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.graphics.RectF
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import androidx.appcompat.widget.AppCompatImageView

/**
 * Картинка, которую можно увеличивать пальцами: щипок, перетаскивание и двойное
 * касание. Для полноэкранного просмотра графика — в ленте статистики увеличения
 * не было вовсе.
 *
 * Своя, а не библиотечная: нужно ровно три жеста, и тянуть ради них зависимость
 * незачем.
 *
 * Показывает и рисунок экрана (Picture) — так увеличивается карточка слова с
 * таблицами: там текст, и он обязан оставаться чётким на любом увеличении.
 */
class ZoomImageView(context: Context) : AppCompatImageView(context) {

    private val drawMatrix = Matrix()
    private var fitScale = 1f

    // От чего считается «увеличено» и докуда можно увеличивать. У картинки это
    // вписанный в экран размер, у карточки — натуральная величина: карточка
    // длиннее экрана, вписанная она нечитаема, и мерить от неё нельзя.
    private var zoomBase = 1f
    private var pendingTopPx: Int? = null

    init {
        scaleType = ScaleType.MATRIX
    }

    val currentScale: Float
        get() = FloatArray(9).also { drawMatrix.getValues(it) }[Matrix.MSCALE_X]

    /** Масштаб, при котором картинка вписана в экран; меньше увеличивать нельзя. */
    val minScale: Float get() = fitScale
    val maxScale: Float get() = zoomBase * MAX_FACTOR

    private val scaleDetector = ScaleGestureDetector(context,
        object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(d: ScaleGestureDetector): Boolean {
                zoomBy(d.scaleFactor, d.focusX, d.focusY)
                return true
            }
        })

    private val gestureDetector = GestureDetector(context,
        object : GestureDetector.SimpleOnGestureListener() {
            override fun onScroll(e1: MotionEvent?, e2: MotionEvent, dx: Float, dy: Float): Boolean {
                drawMatrix.postTranslate(-dx, -dy)
                clamp()
                imageMatrix = drawMatrix
                return true
            }

            override fun onDoubleTap(e: MotionEvent): Boolean {
                val target = if (currentScale > zoomBase * 1.05f) zoomBase else zoomBase * DOUBLE_TAP_FACTOR
                zoomBy(target / currentScale, e.x, e.y)
                return true
            }
        })

    override fun onTouchEvent(event: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(event)
        gestureDetector.onTouchEvent(event)
        return true
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        fit()
        applyStart()
    }

    /** Первая картинка: вписать в экран. */
    fun show(bitmap: Bitmap) {
        setImageBitmap(bitmap)
        fit()
    }

    /**
     * Показать рисунок карточки, а не картинку: в записанном рисунке текст
     * остаётся буквами и при увеличении перерисовывается, а не растягивается
     * пикселями — ради огласовок это и делалось.
     *
     * Открывается в натуральную величину, как на экране, и с той высоты, по
     * которой нажали: карточка длиннее экрана, и вписанная целиком была бы
     * мельче исходной.
     */
    fun showDrawing(drawing: Drawable, startTopPx: Int) {
        pendingTopPx = startTopPx
        setImageDrawable(drawing)
        fit()
        applyStart()
    }

    private fun applyStart() {
        val top = pendingTopPx ?: return
        val d = drawable ?: return
        if (width == 0 || height == 0) return
        if (d.intrinsicWidth <= 0 || d.intrinsicHeight <= 0) return
        pendingTopPx = null
        // Не мельче вписанной: узкая карточка вписывается крупнее натуральной.
        zoomBase = maxOf(1f, fitScale)
        drawMatrix.reset()
        drawMatrix.postScale(zoomBase, zoomBase)
        drawMatrix.postTranslate((width - d.intrinsicWidth * zoomBase) / 2f, -top * zoomBase)
        clamp()
        imageMatrix = drawMatrix
    }

    /**
     * Подменить картинку более подробной, не сдвинув видимое. Большая приходит
     * фоном, и человек к этому времени мог уже увеличить нужный кусок лёгкой —
     * подмена не должна отбросить его к началу.
     */
    fun sharpen(bitmap: Bitmap) {
        val old = (drawable as? BitmapDrawable)?.bitmap
        val ratio = if (old != null && bitmap.width > 0) old.width.toFloat() / bitmap.width else 1f
        drawMatrix.preScale(ratio, ratio)
        fitScale *= ratio
        zoomBase *= ratio
        setImageBitmap(bitmap)
        imageMatrix = drawMatrix
    }

    fun zoomBy(factor: Float, px: Float, py: Float) {
        val current = currentScale
        if (current <= 0f) return
        val target = (current * factor).coerceIn(minScale, maxScale)
        val f = target / current
        drawMatrix.postScale(f, f, px, py)
        clamp()
        imageMatrix = drawMatrix
    }

    private fun fit() {
        val d = drawable ?: return
        if (width == 0 || height == 0) return
        val iw = d.intrinsicWidth.toFloat()
        val ih = d.intrinsicHeight.toFloat()
        if (iw <= 0f || ih <= 0f) return
        fitScale = minOf(width / iw, height / ih)
        zoomBase = fitScale
        drawMatrix.reset()
        drawMatrix.postScale(fitScale, fitScale)
        drawMatrix.postTranslate((width - iw * fitScale) / 2f, (height - ih * fitScale) / 2f)
        imageMatrix = drawMatrix
    }

    /** Не дать утащить картинку за край; меньшую экрана — держать по центру. */
    private fun clamp() {
        val d = drawable ?: return
        val r = RectF(0f, 0f, d.intrinsicWidth.toFloat(), d.intrinsicHeight.toFloat())
        drawMatrix.mapRect(r)
        val dx = when {
            r.width() <= width -> (width - r.width()) / 2f - r.left
            r.left > 0 -> -r.left
            r.right < width -> width - r.right
            else -> 0f
        }
        val dy = when {
            r.height() <= height -> (height - r.height()) / 2f - r.top
            r.top > 0 -> -r.top
            r.bottom < height -> height - r.bottom
            else -> 0f
        }
        drawMatrix.postTranslate(dx, dy)
    }

    companion object {
        const val MAX_FACTOR = 5f
        const val DOUBLE_TAP_FACTOR = 2.5f
    }
}
