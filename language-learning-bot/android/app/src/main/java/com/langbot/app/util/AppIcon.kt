package com.langbot.app.util

import androidx.appcompat.app.AppCompatActivity
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
 */
fun AppCompatActivity.showAppIcon() {
    supportActionBar?.apply {
        setLogo(R.drawable.app_logo)
        setDisplayUseLogoEnabled(true)
        setDisplayShowHomeEnabled(true)
    }
}
