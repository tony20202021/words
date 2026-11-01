package com.langbot.app

import android.content.Intent
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.ChartCache
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf

/**
 * Уйти со статистики туда, куда нужно, а не туда, откуда пришёл.
 *
 * Жалоба владельца: «со статистики сейчас только кнопка назад, она возвращает
 * на предыдущий экран, и он может быть разный — либо сессия обучения, либо
 * главный экран выбора языков». То есть одна и та же кнопка ведёт в два
 * разных места, и какое из них сегодня — заранее не видно.
 *
 * Решение: стрелка остаётся («вернуться»), а в меню появляются два явных
 * перехода («пойти куда хочу»).
 */
@RunWith(RobolectricTestRunner::class)
class StatsNavigationTest {

    private lateinit var server: MockWebServer
    private val u = "u-nav"
    private val l = "lang-he"

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ChartCache.init(ctx)
        UserPrefs.saveUserId(ctx, u)
        server = MockWebServer()
        // Экран навигации от содержимого не зависит: пусть статистика не
        // приедет вовсе — переходы обязаны работать и на пустом экране.
        server.enqueue(MockResponse().setResponseCode(404))
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    private fun open(): StatsActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
            .putExtra("language_id", l).putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StatsActivity::class.java, intent).setup().get()
    }

    @Test
    fun the_menu_offers_both_destinations_by_name() {
        val a = open()
        // Настоящий Menu, который экран сам и наполняет. shadowOf().optionsMenu
        // здесь пуст: системное меню создаётся только при открытии.
        val menu = android.widget.PopupMenu(a, null).menu
        a.onCreateOptionsMenu(menu)
        val titles = (0 until menu.size()).map { menu.getItem(it).title.toString() }

        assertTrue("нет перехода к обучению: $titles", titles.any { it.contains("обучени", true) })
        assertTrue("нет перехода к выбору языка: $titles", titles.any { it.contains("язык", true) })
    }

    @Test
    fun choosing_study_opens_the_study_screen_for_the_same_language() {
        val a = open()
        shadowOf(a).clickMenuItem(StatsActivity.MENU_STUDY)

        val started = shadowOf(a).nextStartedActivity
        assertNotNull("переход к обучению ничего не открыл", started)
        assertEquals(StudyActivity::class.java.name, started.component?.className)
        assertEquals("потерян язык — обучение начнётся не тому",
            l, started.getStringExtra("language_id"))
    }

    @Test
    fun choosing_languages_opens_the_language_list() {
        val a = open()
        shadowOf(a).clickMenuItem(StatsActivity.MENU_LANGUAGES)

        val started = shadowOf(a).nextStartedActivity
        assertNotNull("переход к выбору языка ничего не открыл", started)
        assertEquals(LanguagesActivity::class.java.name, started.component?.className)
    }

    @Test
    fun the_destination_is_reused_and_not_stacked_a_second_time() {
        /*
         * Путь «обучение → статистика → к обучению» без этих флагов положил бы
         * вторую сессию поверх первой: «назад» пришлось бы жать дважды, и по
         * дороге снова показалась бы статистика. CLEAR_TOP со SINGLE_TOP
         * возвращают управление уже открытому экрану.
         */
        val a = open()
        shadowOf(a).clickMenuItem(StatsActivity.MENU_STUDY)
        val flags = shadowOf(a).nextStartedActivity.flags

        assertTrue("нет FLAG_ACTIVITY_CLEAR_TOP — экран ляжет второй копией",
            flags and Intent.FLAG_ACTIVITY_CLEAR_TOP != 0)
        assertTrue("нет FLAG_ACTIVITY_SINGLE_TOP — экран пересоздастся заново",
            flags and Intent.FLAG_ACTIVITY_SINGLE_TOP != 0)
    }

    @Test
    fun the_back_arrow_still_just_closes_the_screen() {
        /*
         * Опора: владелец просил «кнопку назад оставить». Стрелка обязана
         * по-прежнему закрывать экран, а не уводить в новое место.
         */
        val a = open()
        val toolbar = a.findViewById<androidx.appcompat.widget.Toolbar>(R.id.toolbar)
        // Саму стрелку рисует ImageButton внутри тулбара — жмём её, а не
        // обработчик: так проверяется настоящий путь нажатия.
        val arrow = (0 until toolbar.childCount)
            .map { toolbar.getChildAt(it) }
            .filterIsInstance<android.widget.ImageButton>()
            .firstOrNull()
        assertNotNull("в тулбаре нет кнопки «назад» — её просили оставить", arrow)
        arrow!!.performClick()

        assertTrue("стрелка перестала закрывать экран", a.isFinishing)
        assertNull("стрелка начала открывать новый экран", shadowOf(a).nextStartedActivity)
    }
}
