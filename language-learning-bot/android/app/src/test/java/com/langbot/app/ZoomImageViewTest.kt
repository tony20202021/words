package com.langbot.app

import android.graphics.Bitmap
import android.graphics.Matrix
import android.graphics.Picture
import android.graphics.drawable.PictureDrawable
import android.view.View
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.GraphicsMode

/** Увеличение: границы масштаба и подмена на большую без сдвига видимого. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class ZoomImageViewTest {

    private fun laidOut(): ZoomImageView {
        val v = ZoomImageView(ApplicationProvider.getApplicationContext())
        v.measure(View.MeasureSpec.makeMeasureSpec(1000, View.MeasureSpec.EXACTLY),
                  View.MeasureSpec.makeMeasureSpec(1000, View.MeasureSpec.EXACTLY))
        v.layout(0, 0, 1000, 1000)
        return v
    }

    @Test
    fun picture_starts_fitted_to_the_screen() {
        val v = laidOut()
        v.show(Bitmap.createBitmap(500, 400, Bitmap.Config.ARGB_8888))
        assertEquals(2f, v.currentScale, 0.001f)   // 1000/500 — вписана по ширине
    }

    @Test
    fun zoom_stays_between_fit_and_five_times() {
        val v = laidOut()
        v.show(Bitmap.createBitmap(500, 400, Bitmap.Config.ARGB_8888))
        v.zoomBy(100f, 500f, 500f)
        assertEquals(v.maxScale, v.currentScale, 0.001f)
        v.zoomBy(0.0001f, 500f, 500f)
        assertEquals(v.minScale, v.currentScale, 0.001f)
    }

    /**
     * Карточка слова — не картинка: она длиннее экрана, и мерить увеличение от
     * вписанной в экран нельзя. Вписанная впятеро — это всё ещё мельче, чем на
     * самом экране, то есть увеличения бы не было вовсе.
     */
    @Test
    fun a_card_longer_than_the_screen_opens_at_its_own_size() {
        val v = laidOut()
        val picture = Picture()
        picture.beginRecording(1000, 5000)
        picture.endRecording()
        v.showDrawing(PictureDrawable(picture), 0)

        assertEquals("открылась не в натуральную величину", 1f, v.currentScale, 0.001f)
        assertEquals("увеличивать можно не впятеро", 5f, v.maxScale, 0.001f)
        // Уменьшить до целой страницы всё же можно: 1000/5000.
        assertEquals("нельзя уменьшить до целой карточки", 0.2f, v.minScale, 0.001f)
    }

    @Test
    fun a_card_opens_at_the_block_that_was_tapped() {
        val v = laidOut()
        val picture = Picture()
        picture.beginRecording(1000, 5000)
        picture.endRecording()
        v.showDrawing(PictureDrawable(picture), 1200)

        val y = FloatArray(9).also { v.imageMatrix.getValues(it) }[Matrix.MTRANS_Y]
        assertEquals("открылась не с той высоты, по которой нажали", -1200f, y, 0.5f)
    }

    @Test
    fun sharper_picture_keeps_the_visible_size() {
        val v = laidOut()
        v.show(Bitmap.createBitmap(500, 400, Bitmap.Config.ARGB_8888))
        v.zoomBy(2f, 500f, 500f)
        val visibleWidth = 500 * v.currentScale
        v.sharpen(Bitmap.createBitmap(1000, 800, Bitmap.Config.ARGB_8888))
        assertEquals("подмена на большую сдвинула масштаб видимого",
            visibleWidth, 1000 * v.currentScale, 0.5f)
    }
}
