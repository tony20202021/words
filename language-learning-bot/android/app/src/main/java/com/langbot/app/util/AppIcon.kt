package com.langbot.app.util

import android.graphics.drawable.InsetDrawable
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.langbot.app.R

/**
 * Значок приложения в панели сверху.
 *
 * Почему общим местом, а не правкой в каждом экране. Панель настраивают шесть
 * экранов, и общего предка у них нет. Шесть одинаковых правок означают, что
 * седьмой экран про значок забудут — и он будет отличаться от остальных, пока
 * кто-нибудь это не заметит. Здесь одна строка на экран, а решение одно.
 *
 * Со стрелкой «назад» уживается: система ставит значок после неё.
 *
 * Иконка 40 dp в области 46 × 56 dp: справа 6 dp, без лишнего поля слева.
 * Явная ширина нужна, иначе Toolbar резервирует ширину исходного PNG,
 * хотя по высоте ImageView уже уменьшил его до размера панели.
 * При меньшей высоте панели рисунок пропорционально уменьшается.
 */
fun AppCompatActivity.showAppIcon() {
    val значок = ContextCompat.getDrawable(this, R.drawable.app_logo) ?: return
    val density = resources.displayMetrics.density
    // Убираем дополнительный промежуток после стандартной кнопки «назад».
    findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar)
        ?.contentInsetStartWithNavigation = (56 * density + 0.5f).toInt()
    val logo = object : InsetDrawable(значок, 0) {
        override fun getIntrinsicWidth() = (46 * density + 0.5f).toInt()
        override fun getIntrinsicHeight() = (56 * density + 0.5f).toInt()

        override fun onBoundsChange(bounds: android.graphics.Rect) {
            super.onBoundsChange(bounds)
            val size = minOf((40 * density + 0.5f).toInt(), bounds.width(),
                (bounds.height() * 40f / 56f).toInt())
            val left = bounds.left
            val top = bounds.top + (bounds.height() - size) / 2
            значок.setBounds(left, top, left + size, top + size)
        }
    }
    supportActionBar?.apply {
        setLogo(logo)
        setDisplayUseLogoEnabled(true)
        setDisplayShowHomeEnabled(true)
    }
}
