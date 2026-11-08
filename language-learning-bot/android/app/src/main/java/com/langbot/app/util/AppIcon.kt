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
 * ПОЛЯ ВОКРУГ. Своей высоты у логотипа нет: панель растягивает его на всю
 * доступную высоту, и круглый значок упирался в верхнюю и нижнюю границы —
 * владелец: «она сейчас прямо касается верхней и нижней границ». Задать
 * размер напрямую нечем, setLogo берёт только drawable. Поэтому значок
 * обёрнут в InsetDrawable: рисунок тот же, но внутри своих границ он занимает
 * меньше, и вокруг остаётся воздух. Поля одинаковые со всех сторон — иначе
 * круг стал бы овалом.
 */
private const val ПОЛЕ_DP = 6

fun AppCompatActivity.showAppIcon() {
    val значок = ContextCompat.getDrawable(this, R.drawable.app_logo) ?: return
    val поле = (ПОЛЕ_DP * resources.displayMetrics.density + 0.5f).toInt()
    supportActionBar?.apply {
        setLogo(InsetDrawable(значок, поле, поле, поле, поле))
        setDisplayUseLogoEnabled(true)
        setDisplayShowHomeEnabled(true)
    }
}
