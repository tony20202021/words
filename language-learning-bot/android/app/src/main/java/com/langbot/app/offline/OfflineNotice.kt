package com.langbot.app.offline

import android.view.Gravity
import android.view.ViewGroup
import android.widget.TextView

/**
 * Понятное сообщение об отсутствии сети прямо на экране.
 *
 * Экраны языков, настроек и статистики полностью зависят от BLS и ничего не
 * кешируют. Раньше при отказе сети они ловили исключение, показывали Toast с
 * техническим текстом вроде `getLanguages: [ConnectException] ...` — и он
 * исчезал через пару секунд, оставляя пустой экран. Пользователю оставалось
 * гадать, сломалось приложение или просто нет связи.
 *
 * Учебный экран так себя не ведёт: там есть баннер офлайна и работа из кеша.
 * Здесь кешировать нечего, поэтому минимум — сказать, что происходит, и
 * подсказать способ повторить.
 */
object OfflineNotice {

    private const val TAG_ID = 0x0FF11E

    /**
     * Показать сообщение в контейнере экрана, убрав предыдущее.
     * @param what что именно не удалось загрузить — «языки», «настройки», …
     * @param pullToRefresh есть ли на экране обновление жестом
     */
    fun show(container: ViewGroup, what: String, pullToRefresh: Boolean = true) {
        clear(container)
        val hint = if (pullToRefresh) "\n\nПотяните вниз, чтобы повторить." else ""
        val tv = TextView(container.context).apply {
            id = TAG_ID
            text = "📴 Нет связи с сервером\n\nНе удалось загрузить $what. " +
                    "Проверьте подключение к сети.$hint"
            gravity = Gravity.CENTER
            textSize = 16f
            setPadding(48, 96, 48, 96)
        }
        container.addView(tv)
    }

    /** Убрать сообщение — вызывать при успешной загрузке. */
    fun clear(container: ViewGroup) {
        container.findViewById<TextView>(TAG_ID)?.let(container::removeView)
    }
}
