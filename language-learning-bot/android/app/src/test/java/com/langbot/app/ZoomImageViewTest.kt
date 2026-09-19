package com.langbot.app

import android.graphics.Bitmap
import android.view.View
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/** Увеличение: границы масштаба и подмена на большую без сдвига видимого. */
@RunWith(RobolectricTestRunner::class)
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
