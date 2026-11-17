package com.langbot.app.offline

import android.graphics.Color
import android.view.Gravity
import android.view.ViewGroup
import android.widget.TextView
import com.langbot.app.util.TechNotice

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
 *
 * С 17.11.2026 сообщение кладут в слой поверх экрана (R.id.noticeOverlay), а не
 * в столбец содержимого: владелец просил, чтобы технические сообщения не
 * сдвигали экран. Поэтому у него свой фон — под ним может оказаться список.
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
            textSize = 15f
            setBackgroundColor(Color.parseColor(TechNotice.BG))
            setTextColor(Color.parseColor(TechNotice.FG))
            setPadding(48, 40, 48, 40)
        }
        container.addView(tv)
    }

    /** Убрать сообщение — вызывать при успешной загрузке. */
    fun clear(container: ViewGroup) {
        container.findViewById<TextView>(TAG_ID)?.let(container::removeView)
    }
}
