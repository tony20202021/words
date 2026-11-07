package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.ChartCache
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import org.junit.After
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.android.controller.ActivityController

/**
 * Экран статистики говорит про повторения, отсечённые порогом.
 *
 * Разбор 07.11.2026: у живого пользователя настройка «начальный номер слова»
 * стояла на 3000, и 2546 слов ждали повторения ниже порога — они не
 * показались бы никогда. Отбор на занятие фильтрует по этой настройке ВСЕ
 * слова сразу, а не только новые.
 *
 * Владелец выбрал: поведение отбора оставить, но сказать человеку. Молчание
 * тут и было дефектом — узнать о потере было неоткуда.
 */
@RunWith(RobolectricTestRunner::class)
class HiddenReviewsNoticeTest {

    private lateinit var bls: FakeBls
    private var stats: ActivityController<StatsActivity>? = null

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ChartCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        UserPrefs.saveUserId(ctx, "user-1")
        bls = FakeBls(words = (1..6).toList())
        bls.start()
        BLSClient.init(bls.url())
    }

    @After
    fun tearDown() {
        // Экран обязательно закрыть. Оставленный живым StatsActivity
        // продолжает фоновую подкачку графиков, и это видно НЕ здесь, а в
        // чужих проверках: 07.11.2026 из-за него в общем прогоне падали
        // WaitingNoticeTest и AnswerWhileConnectingTest, обе по отдельности
        // зелёные. Соседние проверки этого экрана так и делают.
        stats?.let { runCatching { it.pause().stop().destroy() } }
        bls.shutdown()
    }

    private fun открыть(): String {
        val controller = Robolectric.buildActivity(
            StatsActivity::class.java,
            Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
                .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит"),
        ).setup()
        stats = controller
        val a = controller.get()
        runCatching {
            Screenshots.pumpUntil("статистика приехала", timeoutMs = 25_000) {
                тексты(a).contains("Изучено")
            }
        }
        return тексты(a)
    }

    private fun тексты(a: StatsActivity): String {
        val root: View = a.findViewById(R.id.swipeRefresh) ?: return ""
        val sb = StringBuilder()
        fun walk(v: View) {
            if (v.visibility != View.VISIBLE) return
            if (v is TextView) sb.append(v.text).append('\n')
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return sb.toString()
    }

    @Test
    fun the_screen_says_how_many_reviews_the_threshold_hides() {
        bls.hiddenByStartWord = 2546
        bls.startWord = 3000

        val text = открыть()

        assertTrue("нет числа отсечённых повторений:\n$text", text.contains("2546"))
        assertTrue("не сказано, что это повторения:\n$text",
            text.contains("повторения", ignoreCase = true))
        assertTrue("не назван порог, из-за которого это вышло:\n$text",
            text.contains("3000"))
    }

    @Test
    fun the_screen_stays_quiet_when_nothing_is_hidden() {
        /*
         * Опора. У кого порог не трогали, строки быть не должно: предупреждение,
         * которое висит всегда, перестают читать — и оно не сработает тогда,
         * когда понадобится.
         */
        bls.hiddenByStartWord = 0
        bls.startWord = 1

        val text = открыть()

        assertTrue("статистика вообще не приехала:\n$text", text.contains("Изучено"))
        assertFalse("строка про отсечённые повторения висит без повода:\n$text",
            text.contains("отсечены"))
    }
}
