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
        val collapse = Runnable {
            if (messages(stack).isEmpty()) return@Runnable
            stack.visibility = View.GONE
            badge.text = iconOf(messages(stack).first())
            badge.visibility = View.VISIBLE
        }
        fun expand() {
            stack.removeCallbacks(collapse)
            stack.visibility = View.VISIBLE
            badge.visibility = View.GONE
            stack.postDelayed(collapse, COLLAPSE_MS)
        }
        badge.setOnClickListener { expand() }
        stack.tag = collapse                 // для collapseNow — см. ниже
        stack.viewTreeObserver.addOnGlobalLayoutListener {
            val now = messages(stack)
            val signature = now.joinToString("\n") { it.replace(Regex("\\d"), "") }
            if (now.isEmpty()) {
                // Сообщений нет: значок убрать, слой оставить раскрытым — так
                // следующее сообщение сразу покажется целиком.
                stack.removeCallbacks(collapse)
                badge.visibility = View.GONE
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
     * Свернуть сообщения сразу, не дожидаясь паузы.
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
