package com.langbot.app.util

import android.graphics.Canvas
import android.graphics.Paint
import android.text.SpannableString
import android.text.Spanned
import android.text.style.ReplacementSpan
import kotlin.math.ceil

/** Каждый фрагмент между пробелами переносится как один неделимый элемент. */
fun wholeWords(text: String): CharSequence = SpannableString(text).apply {
    Regex("\\S+").findAll(text).forEach { word ->
        setSpan(WholeWordSpan(), word.range.first, word.range.last + 1,
            Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
    }
}

private class WholeWordSpan : ReplacementSpan() {
    override fun getSize(paint: Paint, text: CharSequence, start: Int, end: Int,
                         fm: Paint.FontMetricsInt?): Int {
        if (fm != null) paint.getFontMetricsInt(fm)
        return ceil(paint.measureText(text, start, end).toDouble()).toInt()
    }

    override fun draw(canvas: Canvas, text: CharSequence, start: Int, end: Int,
                      x: Float, top: Int, y: Int, bottom: Int, paint: Paint) {
        canvas.drawText(text, start, end, x, y.toFloat(), paint)
    }
}
