package com.langbot.app

import android.app.Activity
import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.StoredBundle
import com.langbot.app.prefs.UserPrefs
import com.langbot.app.util.TechNotice
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * Технические сообщения лежат поверх экрана и ничего не сдвигают.
 *
 * Владелец (17.11.2026), со снимком плашки «📴 Офлайн — результаты сохраняются
 * локально (1)…»: «все технические сообщения делать поверх экрана, не сдвигая
 * его вниз; сейчас некоторые вставляются прямо в экран и сдвигают».
 *
 * Плашку соединения на карточке так уже переделали раньше, и её сторожит
 * ConnectionNoticeDoesNotShiftTheCardTest. Здесь — все остальные: совет
 * перезапустить и плашка офлайна на карточке, полоса загрузки, кружки загрузки
 * над списками, полоса «доступна версия».
 *
 * Положение сверяется по раскладке, как на телефоне: окно меряется в размер
 * экрана, и содержимое должно начинаться ровно под панелью приложения — что
 * бы над ним ни было показано.
 */
@RunWith(RobolectricTestRunner::class)
@Config(qualifiers = "w411dp-h891dp-xhdpi")
class TechNoticesDoNotShiftTest {

    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return when {
                    // Версия на сервере новее любой установленной — полоса
                    // «доступна версия» обязана появиться.
                    path.startsWith("/version") -> MockResponse().setResponseCode(200)
                        .setBody("""{"version":"99.0.0","version_code":990000}""")
                    path.startsWith("/languages") -> MockResponse().setResponseCode(200)
                        .setBody("""[{"id":"lang-1","name_ru":"Иврит","name_foreign":"עברית"}]""")
                    else -> MockResponse().setResponseCode(404)
                }
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
        OfflineCache.saveBundle(StoredBundle("user-1", "lang-1", emptyList()))
    }

    /** Разложить окно целиком в размер экрана — как его видит человек. */
    private fun layOut(a: Activity) {
        val dm = a.resources.displayMetrics
        val decor = a.window.decorView
        decor.measure(
            View.MeasureSpec.makeMeasureSpec(dm.widthPixels, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(dm.heightPixels, View.MeasureSpec.EXACTLY))
        decor.layout(0, 0, dm.widthPixels, dm.heightPixels)
    }

    private fun yOf(v: View): Int = IntArray(2).also { v.getLocationInWindow(it) }[1]

    private fun parents(v: View): List<Any> {
        val out = mutableListOf<Any>()
        var p = v.parent
        while (p != null) { out.add(p); p = (p as? View)?.parent }
        return out
    }

    /** Содержимое стоит вплотную под панелью — между ними ничего не вставлено. */
    private fun assertContentRightUnderToolbar(a: Activity, contentId: Int, what: String) {
        layOut(a)
        val toolbar = a.findViewById<View>(R.id.toolbar)
        val content = a.findViewById<View>(contentId)
        assertEquals("$what: содержимое уехало вниз — между панелью и ним что-то " +
            "вставлено в разметку, а не положено поверх",
            yOf(toolbar) + toolbar.height, yOf(content))
    }

    // ── Карточка слова ─────────────────────────────────────────────────────

    private fun study(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
    }

    @Test
    fun study_notices_are_not_inside_the_scrolling_card() {
        val a = study()
        val swipe = a.findViewById<View>(R.id.swipeRefresh)
        for ((id, name) in listOf(R.id.restartNotice to "совет перезапустить",
                                  R.id.staleNotice to "плашка офлайна",
                                  R.id.tvConnection to "плашка соединения",
                                  R.id.loadingBar to "полоса загрузки")) {
            assertFalse("$name внутри прокручиваемой карточки — она её сдвигает",
                parents(a.findViewById(id)).contains(swipe))
        }
    }

    @Test
    fun the_offline_and_restart_notices_do_not_move_the_card() {
        val a = study()
        layOut(a)
        val card = a.findViewById<View>(R.id.cardContent)
        val before = yOf(card)

        // Обе плашки сразу и с длинным текстом — как на снимке владельца.
        a.findViewById<TextView>(R.id.tvStaleSession).text =
            "📴 Офлайн — результаты сохраняются локально (1) и отправятся при подключении"
        a.findViewById<View>(R.id.staleNotice).visibility = View.VISIBLE
        a.findViewById<TextView>(R.id.tvRestartNotice).text =
            "Много ошибок подряд — можно перезапустить сессию"
        a.findViewById<View>(R.id.restartNotice).visibility = View.VISIBLE
        a.findViewById<View>(R.id.loadingBar).visibility = View.VISIBLE
        layOut(a)

        assertTrue("плашка офлайна не раскладывается — проверять нечего",
            a.findViewById<View>(R.id.staleNotice).height > 0)
        assertEquals("карточка уехала вниз от технических плашек", before, yOf(card))
    }

    // ── Списки: языки, статистика, настройки, подсказки ───────────────────

    @Test
    fun the_update_banner_and_the_spinner_do_not_push_the_languages_list() {
        val a = Robolectric.buildActivity(LanguagesActivity::class.java).setup().get()
        Screenshots.pumpUntil("полоса «доступна версия» появилась") {
            TechNotice.find(TechNotice.overlay(a), LanguagesActivity.UPDATE_KEY) != null
        }
        a.findViewById<View>(R.id.progress).visibility = View.VISIBLE
        assertContentRightUnderToolbar(a, R.id.swipeRefresh, "экран языков")
        val banner = TechNotice.find(TechNotice.overlay(a), LanguagesActivity.UPDATE_KEY)!!
        assertTrue("полоса показывает не то: ${banner.text}",
            banner.text.toString().contains("Доступна версия 99.0.0"))
        assertTrue("по полосе нельзя нажать — к обновлению не попасть", banner.isClickable)
    }

    @Test
    fun the_spinner_does_not_push_the_stats_screen() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(StatsActivity::class.java, intent).setup().get()
        a.findViewById<View>(R.id.progress).visibility = View.VISIBLE
        assertContentRightUnderToolbar(a, R.id.swipeRefresh, "экран статистики")
    }

    @Test
    fun the_spinner_does_not_push_the_settings_screen() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), SettingsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(SettingsActivity::class.java, intent).setup().get()
        a.findViewById<View>(R.id.progress).visibility = View.VISIBLE
        assertContentRightUnderToolbar(a, R.id.swipeRefresh, "экран настроек")
    }

    @Test
    fun the_spinner_does_not_push_the_hints_screen() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), HintsActivity::class.java)
            .putExtra("user_id", "user-1").putExtra("word_id", "w1")
            .putExtra("language_id", "lang-1")
        val a = Robolectric.buildActivity(HintsActivity::class.java, intent).setup().get()
        a.findViewById<View>(R.id.progress).visibility = View.VISIBLE
        // У подсказок нет обновления жестом: содержимое — сама прокрутка.
        val scroll = (a.findViewById<ViewGroup>(R.id.hintsContainer).parent as View)
        layOut(a)
        val toolbar = a.findViewById<View>(R.id.toolbar)
        assertEquals("экран подсказок: кружок загрузки сдвинул список",
            yOf(toolbar) + toolbar.height, yOf(scroll))
    }

    @Test
    fun a_stale_no_connection_notice_does_not_outlive_the_next_load() {
        /*
         * Пока сообщения лежали в списке, перерисовка списка стирала их сама.
         * В слое поверх они её переживают — и прежнее «не удалось загрузить
         * настройки» висело бы над настройками, показанными из партии. На
         * экране статистики так и вышло при первом заходе этой правки:
         * связь вернулась, а «нет связи» осталось.
         */
        val intent = Intent(ApplicationProvider.getApplicationContext(), SettingsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(SettingsActivity::class.java, intent).setup().get()
        val stack = TechNotice.overlay(a)
        // Сервер настройки не отдаёт, партии нет — «не удалось загрузить».
        Screenshots.pumpUntil("сказано, что связи нет") { stack.childCount > 0 }

        // Партия появилась, связи по-прежнему нет — настройки из партии.
        OfflineCache.saveBundle(StoredBundle("user-1", "lang-1", emptyList(), cursor = 0,
            settings = mapOf("skip_marked" to true)))
        SettingsActivity::class.java.getDeclaredMethod("loadSettings")
            .apply { isAccessible = true }.invoke(a)
        Screenshots.pumpUntil("настройки из партии показаны") {
            TechNotice.find(stack, SettingsActivity.OFFLINE_KEY) != null
        }
        val тексты = (0 until stack.childCount).map { (stack.getChildAt(it) as TextView).text.toString() }
        assertEquals("над настройками висит прежнее сообщение: $тексты", 1, тексты.size)
        assertTrue(тексты.single().contains("офлайн-партии"))
    }

    // ── Сворачивание в значок ──────────────────────────────────────────────
    //
    // Владелец (17.11.2026): поверх экрана плашка закрывала верх карточки —
    // строку «Слово номер» и значок «знал», а плашка офлайна висит всю
    // офлайн-сессию. Решение владельца: «через пару секунд сворачивать её в
    // маленький значок в углу».

    private fun later(ms: Long) = org.robolectric.shadows.ShadowLooper.idleMainLooper(
        ms, java.util.concurrent.TimeUnit.MILLISECONDS)

    /** Пауза и само сжатие в угол — после этого слой свёрнут. */
    private val свернулось = TechNotice.COLLAPSE_MS + TechNotice.COLLAPSE_ANIM_MS +
        TechNotice.BADGE_ANIM_MS + 100

    /** Раскладка, как после кадра на телефоне: слой узнаёт о переменах. */
    private fun frame(a: Activity) {
        layOut(a)
        TechNotice.overlay(a).viewTreeObserver.dispatchOnGlobalLayout()
    }

    private fun offline(a: StudyActivity, pending: Int) {
        a.findViewById<TextView>(R.id.tvStaleSession).text =
            "📴 Офлайн — результаты сохраняются локально ($pending) и отправятся при подключении"
        a.findViewById<View>(R.id.staleNotice).visibility = View.VISIBLE
        frame(a)
    }

    @Test
    fun a_notice_collapses_into_a_corner_icon_after_a_couple_of_seconds() {
        val a = study()
        layOut(a)
        val card = a.findViewById<View>(R.id.cardContent)
        val before = yOf(card)
        val stack = TechNotice.overlay(a)
        val badge = a.findViewById<TextView>(TechNotice.BADGE_ID)

        offline(a, 1)
        assertEquals("новое сообщение должно сначала показаться целиком",
            View.VISIBLE, stack.visibility)
        assertEquals("значок раньше времени", View.GONE, badge.visibility)

        later(свернулось)
        assertEquals("через пару секунд сообщение не свернулось", View.GONE, stack.visibility)
        assertEquals("значка в углу нет", View.VISIBLE, badge.visibility)
        assertEquals("значок не тот, что у сообщения", "📴", badge.text.toString())
        frame(a)
        assertEquals("карточка сдвинулась при сворачивании", before, yOf(card))
        // Значок — в правом верхнем углу.
        val dm = a.resources.displayMetrics
        val xy = IntArray(2).also { badge.getLocationInWindow(it) }
        assertTrue("значок не у правого края: x=${xy[0]}", xy[0] + badge.width > dm.widthPixels * 0.9)
        assertTrue("значок не у верхнего края: y=${xy[1]}", xy[1] - yOf(a.findViewById(R.id.swipeRefresh)) < badge.height)
    }

    @Test
    fun tapping_the_icon_shows_the_message_again_and_it_collapses_again() {
        val a = study()
        offline(a, 1)
        later(свернулось)
        val stack = TechNotice.overlay(a)
        val badge = a.findViewById<TextView>(TechNotice.BADGE_ID)

        badge.performClick()
        assertEquals("по нажатию на значок сообщение не развернулось", View.VISIBLE, stack.visibility)
        assertEquals(View.GONE, badge.visibility)
        later(свернулось)
        assertEquals("развёрнутое по нажатию не свернулось снова", View.GONE, stack.visibility)
    }

    @Test
    fun a_new_count_does_not_pop_the_message_up_again_but_a_new_message_does() {
        val a = study()
        offline(a, 1)
        later(свернулось)
        val stack = TechNotice.overlay(a)

        // После каждого ответа офлайн «(1)» становится «(2)» — это не новость.
        offline(a, 2)
        assertEquals("плашка выпрыгивает на каждом ответе из-за счётчика",
            View.GONE, stack.visibility)

        // А совет перезапустить — новость.
        a.findViewById<TextView>(R.id.tvRestartNotice).text = "Много ошибок — можно перезапустить сессию"
        a.findViewById<View>(R.id.restartNotice).visibility = View.VISIBLE
        frame(a)
        assertEquals("новое сообщение не показалось целиком", View.VISIBLE, stack.visibility)
    }

    @Test
    fun without_messages_there_is_no_icon() {
        val a = study()
        offline(a, 1)
        later(свернулось)
        a.findViewById<View>(R.id.staleNotice).visibility = View.GONE
        frame(a)
        assertEquals("сообщений нет, а значок остался",
            View.GONE, a.findViewById<View>(TechNotice.BADGE_ID).visibility)
        assertEquals("слой остался свёрнутым — следующее сообщение не покажется",
            View.VISIBLE, TechNotice.overlay(a).visibility)
    }

    @Test
    fun a_collapsed_notice_does_not_keep_relaying_the_screen() {
        /*
         * Слой следит за сообщениями по раскладке. Первая версия на каждой
         * раскладке заново ставила значку текст, а это новая раскладка: экран
         * перекладывался без конца, и прогон проверок завис.
         *
         * Без ожидания по часам: при поломке оно само зависает, а не падает.
         * Сворачиваем сразу и делаем один кадр — после него значок не должен
         * просить новой раскладки.
         */
        val a = study()
        offline(a, 1)
        TechNotice.collapseNow(a)
        val badge = a.findViewById<View>(TechNotice.BADGE_ID)
        assertEquals("не свернулось", View.VISIBLE, badge.visibility)
        frame(a)
        assertFalse("свёрнутый слой на каждом кадре просит новую раскладку — " +
            "экран будет перекладываться без конца", badge.isLayoutRequested)
    }

    /** Конечные значения движения по свойствам: scaleX, scaleY, alpha. */
    private fun targets(m: android.animation.AnimatorSet): Map<String, Float> =
        m.childAnimations.filterIsInstance<android.animation.ObjectAnimator>()
            .associate { (it.propertyName ?: "") to (it.animatedValue as Float) }

    @Test
    fun the_notice_shrinks_into_the_corner_instead_of_vanishing() {
        /*
         * Владелец (17.11.2026): «он переходит с анимацией? или просто в одном
         * месте исчезает, в другом появляется?» — и попросил движение.
         *
         * По ходу движение в Robolectric не подсмотреть: кадры анимации там
         * прокручиваются разом. Поэтому спрашиваем у запущенной анимации, что
         * она двигала, куда и сколько, — и проверяем, чем всё кончилось.
         */
        val a = study()
        offline(a, 1)
        val stack = TechNotice.overlay(a)
        later(свернулось)

        val m = TechNotice.motion(stack)
        assertTrue("плашка исчезла без движения", m != null)
        assertEquals("сжатие длится не столько", TechNotice.COLLAPSE_ANIM_MS, m!!.duration)
        val к = targets(m)
        assertEquals("плашка сжималась не до значка: $к", TechNotice.SHRUNK, к["scaleX"]!!, 0.01f)
        assertEquals("плашка сжималась не до значка: $к", TechNotice.SHRUNK, к["scaleY"]!!, 0.01f)
        assertEquals("плашка не гасла по пути: $к", 0f, к["alpha"]!!, 0.01f)
        assertEquals("сжималась не к правому краю", stack.width.toFloat(), stack.pivotX, 1f)
        assertEquals("сжималась не к верхнему краю", 0f, stack.pivotY, 1f)

        val badge = a.findViewById<View>(TechNotice.BADGE_ID)
        val b = TechNotice.motion(badge)
        assertTrue("значок появился без движения", b != null)
        assertEquals("значок не дорос до своего размера", 1f, targets(b!!)["scaleX"]!!, 0.01f)

        assertEquals(View.GONE, stack.visibility)
        assertEquals(View.VISIBLE, badge.visibility)
        assertEquals("значок остался недоросшим", 1f, badge.scaleX, 0.01f)
    }

    @Test
    fun tapping_the_icon_unfolds_the_notice_from_the_corner() {
        val a = study()
        offline(a, 1)
        later(свернулось)
        val stack = TechNotice.overlay(a)
        val сжатие = TechNotice.motion(stack)

        a.findViewById<View>(TechNotice.BADGE_ID).performClick()
        val m = TechNotice.motion(stack)
        assertTrue("плашка появилась без движения", m != null && m !== сжатие)
        assertEquals("разворот длится не столько", TechNotice.EXPAND_ANIM_MS, m!!.duration)
        assertEquals("разворачивалась не из правого угла", stack.width.toFloat(), stack.pivotX, 1f)
        assertEquals("разворачивалась не из верхнего угла", 0f, stack.pivotY, 1f)
        later(TechNotice.EXPAND_ANIM_MS + 50)
        assertEquals("плашка не развернулась до конца", 1f, stack.scaleX, 0.01f)
        assertEquals("плашка осталась полупрозрачной", 1f, stack.alpha, 0.01f)
    }

    @Test
    fun after_collapsing_the_next_message_shows_at_full_size() {
        /*
         * Сжатие оставляет у плашки масштаб 0,12 и прозрачность 0. Не вернуть
         * их — и следующее сообщение после пустой паузы показалось бы
         * невидимой точкой в углу.
         */
        val a = study()
        offline(a, 1)
        later(свернулось)
        a.findViewById<View>(R.id.staleNotice).visibility = View.GONE
        frame(a)
        a.findViewById<TextView>(R.id.tvRestartNotice).text = "Много ошибок — можно перезапустить сессию"
        a.findViewById<View>(R.id.restartNotice).visibility = View.VISIBLE
        frame(a)
        val stack = TechNotice.overlay(a)
        assertEquals(View.VISIBLE, stack.visibility)
        assertEquals("новое сообщение показалось сжатым", 1f, stack.scaleX, 0.01f)
        assertEquals("новое сообщение показалось прозрачным", 1f, stack.alpha, 0.01f)
    }

    @Test
    fun the_icon_is_the_first_picture_of_the_message() {
        assertEquals("📴", TechNotice.iconOf("📴 Офлайн — результаты"))
        assertEquals("⏰", TechNotice.iconOf("⏰ Сессия устарела"))
        assertEquals("⬆", TechNotice.iconOf("⬆ Доступна версия 6.6.0"))
        assertEquals("⚠️", TechNotice.iconOf("⚠️ Внимание"))
        assertEquals("ℹ️", TechNotice.iconOf("Много ошибок подряд"))
    }

    // ── Цвет значка ───────────────────────────────────────────────────────
    //
    // Владелец (18.11.2026): «сейчас иконка всегда желто-оранжевая — можно ли
    // её сделать тем же цветом, что окно самого уведомления?» Плашки разные:
    // офлайн на карточке голубой, «доступна версия» синяя, связь жёлтая.

    private fun fill(badge: View): Int =
        (badge.background as android.graphics.drawable.GradientDrawable).color!!.defaultColor

    private fun color(hex: String) = android.graphics.Color.parseColor(hex)

    @Test
    fun the_icon_takes_the_colours_of_its_notice_and_follows_a_new_one() {
        val a = study()
        val badge = a.findViewById<TextView>(TechNotice.BADGE_ID)

        offline(a, 1)                              // голубая плашка офлайна
        later(свернулось)
        assertEquals("значок не цвета плашки офлайна", color("#CCE5FF"), fill(badge))
        assertEquals("знак на значке не цвета текста плашки", color("#004085"), badge.currentTextColor)

        // На её место пришла жёлтая плашка связи — значок перекрашивается.
        a.findViewById<View>(R.id.staleNotice).visibility = View.GONE
        a.findViewById<TextView>(R.id.tvConnection).apply {
            text = "⚠️ Сервер не отвечает"
            visibility = View.VISIBLE
        }
        frame(a)
        later(свернулось)
        assertEquals("значок остался цвета прежней плашки", color("#FFF3CD"), fill(badge))
        assertEquals(color("#856404"), badge.currentTextColor)
    }

    @Test
    fun the_icon_of_the_update_banner_is_blue_like_the_banner() {
        val a = Robolectric.buildActivity(LanguagesActivity::class.java).setup().get()
        Screenshots.pumpUntil("полоса «доступна версия» появилась") {
            TechNotice.find(TechNotice.overlay(a), LanguagesActivity.UPDATE_KEY) != null
        }
        frame(a)
        later(свернулось)
        val badge = a.findViewById<TextView>(TechNotice.BADGE_ID)
        assertEquals("не свернулось", View.VISIBLE, badge.visibility)
        assertEquals("значок полосы обновления не синий", color("#1565C0"), fill(badge))
        assertEquals("стрелка на синем не белая", color("#FFFFFF"), badge.currentTextColor)
    }
}
