package com.langbot.app.util

import android.app.Activity
import android.graphics.Color
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import com.langbot.app.R

/**
 * Технические сообщения — поверх экрана, а не в его столбце.
 *
 * Владелец (17.11.2026): «все технические сообщения делать поверх экрана, не
 * сдвигая его вниз; сейчас некоторые вставляются прямо в экран и сдвигают».
 * Плашку соединения на карточке так уже переделали раньше, по той же жалобе:
 * встроенная в столбец, она сдвигала всё вниз, и по нижней части экрана это
 * читалось как переход к следующему слову. Остальные сообщения — «офлайн»,
 * «связи нет», «доступна версия» — по-прежнему вставлялись в содержимое.
 *
 * У каждого экрана в разметке есть слой R.id.noticeOverlay: вертикальная
 * стопка у верхнего края, поднятая над содержимым. Сообщения кладутся туда,
 * друг под другом; содержимое под ними не двигается ни при появлении, ни при
 * исчезновении. Нажатия мимо сообщений проходят к содержимому: сам слой их не
 * перехватывает.
 *
 * Сообщение узнаётся по ключу: показать второй раз с тем же ключом — значит
 * обновить текст, а не добавить копию.
 */
object TechNotice {

    /** Цвета предупреждения — те же, что у плашки соединения на карточке. */
    const val BG = "#FFF3CD"
    const val FG = "#856404"

    fun overlay(activity: Activity): LinearLayout = activity.findViewById(R.id.noticeOverlay)

    /** Показать (или обновить) сообщение с ключом [key]. */
    fun show(activity: Activity, key: String, text: String,
             bg: String = BG, fg: String = FG, onClick: (() -> Unit)? = null): TextView {
        val stack = overlay(activity)
        val tv = find(stack, key) ?: TextView(activity).also { new ->
            new.tag = key
            new.textSize = 13f
            val d = activity.resources.displayMetrics.density
            new.setPadding((12 * d).toInt(), (10 * d).toInt(), (12 * d).toInt(), (10 * d).toInt())
            stack.addView(new, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT))
        }
        tv.text = text
        tv.setBackgroundColor(Color.parseColor(bg))
        tv.setTextColor(Color.parseColor(fg))
        if (onClick != null) {
            tv.isClickable = true
            tv.setOnClickListener { onClick() }
        } else {
            tv.setOnClickListener(null)
            tv.isClickable = false
        }
        tv.visibility = View.VISIBLE
        return tv
    }

    /** Убрать сообщение с ключом [key], если оно есть. */
    fun hide(activity: Activity, key: String) {
        val stack = overlay(activity)
        find(stack, key)?.let(stack::removeView)
    }

    /** Сообщение с ключом [key] или null. */
    fun find(stack: ViewGroup, key: String): TextView? =
        (0 until stack.childCount).map { stack.getChildAt(it) }
            .firstOrNull { it.tag == key } as? TextView

    // ── Сворачивание в значок ──────────────────────────────────────────────

    /**
     * Через сколько сообщение сворачивается в значок.
     *
     * Владелец (17.11.2026): поверх экрана плашка закрывала верх карточки —
     * строку «Слово номер» и значок «знал», а плашка офлайна висит всю
     * офлайн-сессию. Выбрал: «через пару секунд сворачивать её в маленький
     * значок в углу». Две с половиной секунды — столько читается самая
     * длинная плашка, офлайновая, в две строки.
     */
    const val COLLAPSE_MS = 2500L

    /** Сколько длится сжатие плашки в угол и разворот обратно. */
    const val COLLAPSE_ANIM_MS = 350L
    const val EXPAND_ANIM_MS = 250L
    const val BADGE_ANIM_MS = 150L

    /** До какого размера сжимается плашка перед тем, как стать значком. */
    const val SHRUNK = 0.12f
    /** С какого размера вырастает значок. */
    private const val BADGE_FROM = 0.4f

    /** id значка свёрнутых сообщений — для проверок. */
    val BADGE_ID = View.generateViewId()

    /**
     * Включить сворачивание сообщений на экране [activity].
     *
     * Новое сообщение показывается целиком, через [COLLAPSE_MS] слой прячется,
     * а в правом верхнем углу остаётся значок — первый знак сообщения (📴, ⏰,
     * ⬆). Нажатие на значок разворачивает сообщения снова, и через ту же паузу
     * они опять сворачиваются. Нет сообщений — нет и значка.
     *
     * За слоем следим по раскладке, а не по вызовам: показывают и меняют
     * сообщения в десятке мест (плашки карточки — прямо из разметки), и любое
     * забытое место показывало бы сообщение навсегда. Что сообщение новое,
     * решает его текст без цифр: плашка офлайна после каждого ответа меняет
     * «(1)» на «(2)», и без этого она выпрыгивала бы снова на каждом слове.
     */
    fun collapsing(activity: Activity) {
        val stack = overlay(activity)
        val frame = stack.parent as? ViewGroup ?: return
        val d = activity.resources.displayMetrics.density
        val badge = TextView(activity).apply {
            id = BADGE_ID
            textSize = 16f
            gravity = android.view.Gravity.CENTER
            val p = (6 * d).toInt()
            setPadding(p, p, p, p)
            minWidth = (32 * d).toInt()
            minHeight = (32 * d).toInt()
            elevation = 8 * d
            background = android.graphics.drawable.GradientDrawable().apply {
                shape = android.graphics.drawable.GradientDrawable.OVAL
                setColor(Color.parseColor(BG))
                setStroke((1 * d).toInt().coerceAtLeast(1), Color.parseColor(FG))
            }
            contentDescription = "Показать сообщение"
            visibility = View.GONE
        }
        frame.addView(badge, android.widget.FrameLayout.LayoutParams(
            android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
            android.widget.FrameLayout.LayoutParams.WRAP_CONTENT,
            android.view.Gravity.TOP or android.view.Gravity.END).apply {
                val m = (4 * d).toInt()
                setMargins(m, m, m, m)
            })

        var shown = ""                       // подпись сообщений, уже показанных целиком

        // Сворачивание и разворачивание — движением, а не подменой.
        //
        // Владелец (17.11.2026): «он переходит с анимацией? или просто в одном
        // месте исчезает, в другом появляется?» — просил движение. Плашка
        // сжимается к правому верхнему углу и гаснет, на её месте вырастает
        // значок; по нажатию плашка разворачивается из того же угла. Видно,
        // куда делось сообщение и откуда оно вернулось.
        //
        // Масштаб — свойство рисования, раскладку он не трогает: под плашкой
        // ничего не двигается и во время движения.
        /**
         * Запустить движение и запомнить его (см. [motion]).
         *
         * ObjectAnimator, а не ViewPropertyAnimator: у запущенной анимации
         * можно спросить, что она двигает, куда и сколько. В Robolectric кадры
         * анимации прокручиваются разом, и по ходу движение не подсмотреть —
         * проверка сверяет, что оно запущено и куда ведёт.
         */
        fun play(view: View, to: Float, alphaTo: Float, ms: Long,
                 interpolator: android.animation.TimeInterpolator,
                 then: (() -> Unit)? = null) {
            val set = android.animation.AnimatorSet()
            set.playTogether(
                android.animation.ObjectAnimator.ofFloat(view, View.SCALE_X, to),
                android.animation.ObjectAnimator.ofFloat(view, View.SCALE_Y, to),
                android.animation.ObjectAnimator.ofFloat(view, View.ALPHA, alphaTo))
            set.duration = ms
            set.interpolator = interpolator
            if (then != null) set.addListener(object : android.animation.AnimatorListenerAdapter() {
                // onAnimationEnd приходит и после отмены — а отменённое
                // движение доигрывать нельзя: его прервало новое сообщение.
                var cancelled = false
                override fun onAnimationCancel(animation: android.animation.Animator) { cancelled = true }
                override fun onAnimationEnd(animation: android.animation.Animator) {
                    if (!cancelled) then()
                }
            })
            view.setTag(R.id.noticeOverlay, set)
            set.start()
        }
        fun stop(view: View) {
            (view.getTag(R.id.noticeOverlay) as? android.animation.Animator)?.cancel()
        }
        fun resetStack() {
            stop(stack)
            stack.scaleX = 1f; stack.scaleY = 1f; stack.alpha = 1f
        }
        fun pivotToCorner() {
            stack.pivotX = stack.width.toFloat()
            stack.pivotY = 0f
        }
        /** Свёрнутое состояние — сразу, без движения. */
        val collapsed = Runnable {
            // Сообщения успели убрать, пока плашка сжималась, — вернуть ей
            // размер, иначе она так и осталась бы невидимой точкой.
            if (messages(stack).isEmpty()) { resetStack(); return@Runnable }
            stack.visibility = View.GONE
            // Масштаб возвращаем уже невидимой плашке: иначе следующее
            // сообщение показалось бы в виде точки в углу.
            stack.scaleX = 1f; stack.scaleY = 1f; stack.alpha = 1f
            val icon = iconOf(messages(stack).first())
            if (badge.text.toString() != icon) badge.text = icon
            badge.visibility = View.VISIBLE
        }
        val collapse = Runnable {
            if (messages(stack).isEmpty() || stack.visibility != View.VISIBLE) return@Runnable
            pivotToCorner()
            play(stack, SHRUNK, 0f, COLLAPSE_ANIM_MS,
                 android.view.animation.AccelerateInterpolator()) {
                collapsed.run()
                // Значок вырастает на месте, куда сжалась плашка.
                badge.scaleX = BADGE_FROM; badge.scaleY = BADGE_FROM; badge.alpha = 0f
                play(badge, 1f, 1f, BADGE_ANIM_MS,
                     android.view.animation.DecelerateInterpolator())
            }
        }
        fun expand() {
            stack.removeCallbacks(collapse)
            val fromCorner = badge.visibility == View.VISIBLE
            stop(badge)
            badge.visibility = View.GONE
            resetStack()
            stack.visibility = View.VISIBLE
            if (fromCorner) {
                // Обратный путь: из угла, где стоял значок.
                pivotToCorner()
                stack.scaleX = SHRUNK; stack.scaleY = SHRUNK; stack.alpha = 0f
                play(stack, 1f, 1f, EXPAND_ANIM_MS,
                     android.view.animation.DecelerateInterpolator())
            }
            stack.postDelayed(collapse, COLLAPSE_MS)
        }
        badge.setOnClickListener { expand() }
        stack.tag = collapsed                // для collapseNow — см. ниже
        stack.viewTreeObserver.addOnGlobalLayoutListener {
            val now = messages(stack)
            val signature = now.joinToString("\n") { it.replace(Regex("\\d"), "") }
            if (now.isEmpty()) {
                // Сообщений нет: значок убрать, слой оставить раскрытым — так
                // следующее сообщение сразу покажется целиком.
                stack.removeCallbacks(collapse)
                stop(badge)
                badge.visibility = View.GONE
                resetStack()
                stack.visibility = View.VISIBLE
                shown = ""
            } else if (signature != shown) {
                shown = signature
                expand()
            } else if (badge.visibility == View.VISIBLE) {
                // Тот же текст с другими цифрами — значок обновить, не раскрывая.
                //
                // Только если значок и правда другой. setText перекладывает
                // экран даже тем же текстом, раскладка снова зовёт сюда — и
                // свёрнутый слой перекладывал экран без конца: на первом
                // прогоне проверки зависли, на телефоне это жгло бы батарею.
                val icon = iconOf(now.first())
                if (badge.text.toString() != icon) badge.text = icon
            }
        }
    }

    /**
     * Последнее запущенное движение плашки или значка — для проверок.
     *
     * Смотреть движение по ходу в Robolectric нельзя: кадры анимации там
     * прокручиваются разом, а в режиме кадров по часам не идут вовсе. Зато
     * можно спросить у запущенной анимации, что, куда и сколько она двигает.
     */
    fun motion(view: View): android.animation.AnimatorSet? =
        view.getTag(R.id.noticeOverlay) as? android.animation.AnimatorSet

    /**
     * Свернуть сообщения сразу, не дожидаясь паузы и без движения.
     *
     * Для проверок: ожидание по часам в проверке, где ищут бесконечную
     * раскладку, само зависает при поломке, а не падает.
     */
    fun collapseNow(activity: Activity) {
        (overlay(activity).tag as? Runnable)?.run()
    }

    /** Тексты показанных сообщений слоя — сверху вниз. */
    fun messages(stack: ViewGroup): List<String> {
        fun texts(v: View): List<String> = when {
            v.visibility != View.VISIBLE -> emptyList()
            v is TextView -> if (v.text.isNotBlank()) listOf(v.text.toString()) else emptyList()
            v is ViewGroup -> (0 until v.childCount).flatMap { texts(v.getChildAt(it)) }
            else -> emptyList()
        }
        // Одна плашка — одно сообщение, даже если в ней текст и ссылка.
        return (0 until stack.childCount).map { texts(stack.getChildAt(it)).joinToString(" ") }
            .filter { it.isNotEmpty() }
    }

    /** Значок сообщения: его первый символ-картинка, иначе «ℹ️». */
    fun iconOf(text: String): String {
        val t = text.trim()
        if (t.isEmpty()) return "ℹ️"
        val first = t.codePointAt(0)
        val type = Character.getType(first)
        val picture = type == Character.OTHER_SYMBOL.toInt() ||
            type == Character.MATH_SYMBOL.toInt() || first >= 0x2190 && !Character.isLetterOrDigit(first)
        if (!picture) return "ℹ️"
        // Символ с селектором варианта (⚠️, ⬆️) — вместе с селектором.
        var end = Character.charCount(first)
        if (end < t.length && t[end] == '️') end++
        return t.substring(0, end)
    }
}
