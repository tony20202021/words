package com.langbot.app

import android.content.Intent
import android.graphics.drawable.BitmapDrawable
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.ChartCache
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.android.controller.ActivityController
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * Матрица: экраны × обрывы связи × возвращения связи, и на каждом шаге —
 * проверка счётчиков.
 *
 * Зачем. Владелец прошёл длинный офлайн в самолёте: приложение не упало и
 * слова показывались, но «есть явные ошибки в последовательности переключения
 * экранов по кнопке „ой всё-таки не знаю“, явные ошибки со счётчиками на
 * экранах слова и ошибки в графиках статистики».
 *
 * Отдельные проверки до сих пор смотрели на один экран и один ответ сервера.
 * Счётчики так не ловятся: они живут в череде «ответил — записалось — пришло
 * следующее», и ломаются именно на стыках — когда связь пропала между двумя
 * половинами этой череды.
 *
 * Поэтому здесь: поддельный сервер со своей памятью (FakeBls), сценарии из
 * шагов, и после КАЖДОГО шага — один и тот же набор утверждений о счётчиках:
 *
 *   правильных + ошибок = готово;   готово ≤ размер круга;
 *   позиция ≤ размер круга;         ни один счётчик не убывает внутри круга.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class OfflineMatrixTest {

    private lateinit var bls: FakeBls
    private var study: ActivityController<StudyActivity>? = null
    private var stats: ActivityController<StatsActivity>? = null

    /** Последние увиденные счётчики — по ним проверяется, что они не убывают. */
    private var lastDone = 0
    private var lastPos = 0

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ChartCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        File(ctx.filesDir, "charts").deleteRecursively()
        UserPrefs.saveUserId(ctx, "user-1")
        bls = FakeBls()
        bls.start()
        BLSClient.init(bls.url())
    }

    @After
    fun tearDown() {
        study?.let { runCatching { it.pause().stop().destroy() } }
        stats?.let { runCatching { it.pause().stop().destroy() } }
        bls.shutdown()
    }

    // ── шаги сценария ────────────────────────────────────────────────────

    private fun openStudy() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        study = Robolectric.buildActivity(StudyActivity::class.java, intent).setup()
        Screenshots.pumpUntil("карточка слова показана") { buttons().isNotEmpty() }
    }

    private fun openStats() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StatsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        stats = Robolectric.buildActivity(StatsActivity::class.java, intent).setup()
        // Экран считается открытым, когда он хоть что-то сказал: числа, картинки
        // или объяснение, почему их нет.
        Screenshots.pumpUntil("статистика что-то показала") {
            statsText().isNotBlank() || statsImages().isNotEmpty()
        }
    }

    private fun backFromStats() {
        stats?.let { it.pause().stop().destroy() }
        stats = null
        study?.let { it.start().resume(); Screenshots.pumpUntil("вернулись к слову") { buttons().isNotEmpty() } }
    }

    /** Выключить сеть — но сперва дать телефону дочитать офлайн-партию. */
    private fun netOff() {
        if (study != null && bls.online) {
            runCatching {
                Screenshots.pumpUntil("офлайн-партия скачана", timeoutMs = 10_000) {
                    OfflineCache.loadBundle("user-1", "lang-1") != null
                }
            }
        }
        bls.online = false
    }
    private fun netOn() { bls.online = true }

    private fun study(): StudyActivity = study!!.get()

    private fun buttons(): List<MaterialButton> {
        val a = study ?: return emptyList()
        val out = mutableListOf<MaterialButton>()
        fun walk(v: View) {
            if (v is MaterialButton) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(a.get().findViewById<ViewGroup>(R.id.buttonRow))
        walk(a.get().findViewById<ViewGroup>(R.id.banButtonRow))
        return out
    }

    /**
     * Нажать кнопку и дождаться, пока экран ОТВЕТИТ.
     *
     * Ждать «появились кнопки» нельзя: они и так на месте — те же, что были.
     * Поэтому ждём смену набора кнопок или текста карточки; если за отведённое
     * время ничего не изменилось, идём дальше (бывает и так: «Дальше» на
     * последнем слове просто закрывает круг).
     */
    private fun click(contains: String) {
        val btn = buttons().firstOrNull { it.text.contains(contains) }
            ?: fail("кнопки «$contains» нет, есть: ${buttons().map { it.text }}; " +
                "экран: ${studyText().replace("\n", " ").take(160)}; " +
                "сообщение: ${org.robolectric.shadows.ShadowToast.getTextOfLatestToast()}; " +
                "партия: ${OfflineCache.loadBundle("user-1", "lang-1")?.words?.size}").let { return }
        val before = buttons().map { it.text.toString() } to cardText()
        btn.performClick()
        runCatching {
            Screenshots.pumpUntil("экран ответил на «$contains»", timeoutMs = 25_000) {
                (buttons().map { it.text.toString() } to cardText()) != before
            }
        }
        checkCounters("после «$contains»")
    }

    /** Текст ВИДИМОГО: скрытая надпись остаётся в дереве и врала бы проверкам. */
    private fun visibleText(root: View, skip: Int = 0): String {
        val sb = StringBuilder()
        fun walk(v: View) {
            if (skip != 0 && v.id == skip) return
            if (v.visibility != View.VISIBLE) return
            if (v is TextView) sb.append(v.text).append('\n')
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return sb.toString()
    }

    private fun studyText(): String {
        val a = study ?: return ""
        return visibleText(a.get().findViewById(R.id.swipeRefresh))
    }

    /**
     * Карточка без плашки «соединение нестабильно».
     *
     * По этому снимку ждём, что экран ОТВЕТИЛ на нажатие. Со всем текстом
     * подряд ожидание кончалось раньше времени: при пропавшей сети первой
     * появляется строка «Попытка 2 из 2, ждём до 6 с…», текст экрана меняется,
     * и проверка шла дальше, пока нажатие ещё висело в сети.
     */
    private fun cardText(): String {
        val a = study ?: return ""
        return visibleText(a.get().findViewById(R.id.swipeRefresh), skip = R.id.restartNotice)
    }

    private fun statsText(): String {
        val a = stats ?: return ""
        return visibleText(a.get().findViewById(R.id.statsContainer))
    }

    private fun statsImages(): List<ImageView> {
        val a = stats ?: return emptyList()
        val out = mutableListOf<ImageView>()
        fun walk(v: View) {
            if (v is ImageView && v.drawable is BitmapDrawable) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(a.get().findViewById<ViewGroup>(R.id.statsContainer))
        return out
    }

    private fun statsSpinners(): List<View> {
        val a = stats ?: return emptyList()
        val out = mutableListOf<View>()
        fun walk(v: View) {
            if (v is ProgressBar) out += v
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(a.get().findViewById<ViewGroup>(R.id.statsContainer))
        return out
    }

    // ── утверждения, одинаковые для всех сценариев ───────────────────────

    private fun int(re: Regex, text: String): Int? =
        re.find(text)?.groupValues?.get(1)?.toIntOrNull()

    /**
     * Счётчики на экране слова должны сходиться между собой.
     *
     * «Готово» — это ответы, то есть правильные плюс ошибки. Позиция в круге не
     * может обогнать его размер (у владельца висело «124 из 121»). И ни один из
     * них не убывает, пока идёт круг: убывание значит, что экран показал старое
     * состояние поверх нового.
     */
    private fun checkCounters(where: String) {
        val t = studyText()
        val pos = int(Regex("в сессии: (\\d+) из"), t)
        val total = int(Regex("в сессии: \\d+ из (\\d+)"), t)
        val correct = int(Regex("(\\d+) правильн"), t) ?: 0
        val wrong = int(Regex("(\\d+) ошиб"), t) ?: 0
        val done = int(Regex("готово (\\d+) из"), t)
        val barTotal = int(Regex("готово \\d+ из (\\d+)"), t)

        if (done != null) {
            assertTrue("$where: готово ($done) не равно правильным ($correct) плюс ошибкам ($wrong)\n$t",
                done == correct + wrong)
            if (barTotal != null) assertTrue("$where: готово ($done) больше круга ($barTotal)\n$t",
                done <= barTotal)
            assertTrue("$where: счётчик «готово» убыл с $lastDone до $done\n$t", done >= lastDone)
            lastDone = done
        }
        if (pos != null && total != null) {
            assertTrue("$where: позиция ($pos) обогнала круг ($total)\n$t", pos <= total)
            assertTrue("$where: позиция убыла с $lastPos до $pos\n$t", pos >= lastPos)
            lastPos = pos
        }
        assertTrue("$where: отрицательные счётчики\n$t", correct >= 0 && wrong >= 0)
    }

    /** Статистика: либо числа и картинки, либо объяснение. Вечного ожидания быть не должно. */
    private fun checkStatsSettled(where: String) {
        // Ждём не «нет крутяшек» — их нет и до того, как экран собрался, — а
        // чтобы экран что-то сказал: картинки, числа или объяснение.
        runCatching {
            Screenshots.pumpUntil("$where: статистика договорила", timeoutMs = 25_000) {
                val t = statsText()
                statsSpinners().isEmpty() && (statsImages().isNotEmpty() ||
                    t.contains("Знаю") || t.contains("Нет связи") ||
                    t.contains("Связи нет") || t.contains("с прошлого раза") ||
                    t.contains("Не хватило памяти") || t.contains("Нет данных"))
            }
        }
        val text = statsText()
        val shown = statsImages().isNotEmpty() || text.contains("Знаю") ||
            text.contains("Нет связи") || text.contains("Связи нет") ||
            text.contains("с прошлого раза") ||
            text.contains("Не хватило памяти") || text.contains("Нет данных")
        assertTrue("$where: экран статистики ничего не показал и ничего не объяснил\n" +
            "текст: [$text] картинок: ${statsImages().size} " +
            "в кеше есть: ${ChartCache.hasAny("user-1", "lang-1")} " +
            "версия в кеше: ${ChartCache.version("user-1", "lang-1")} " +
            "картинка 1/words_studied: ${ChartCache.get("user-1", "lang-1", 1, "words_studied")?.size} " +
            "сообщение: ${org.robolectric.shadows.ShadowToast.getTextOfLatestToast()}", shown)
        assertTrue("$where: разделы графиков задвоились\n$text",
            Regex("Графики").findAll(text).count() <= 1)
    }

    private fun resetRound() { lastDone = 0; lastPos = 0 }

    // ── сценарии ─────────────────────────────────────────────────────────

    @Test
    fun online_all_the_way() {
        openStudy(); checkCounters("старт")
        click("Знаю"); click("К следующему слову")
        click("Не знаю"); click("Дальше")
        openStats(); checkStatsSettled("после двух ответов")
        backFromStats()
        click("Знаю"); click("К следующему слову")
    }

    @Test
    fun network_dies_before_the_first_word() {
        netOff()
        // Партии ещё нет — экран обязан сказать об этом, а не промолчать.
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        study = Robolectric.buildActivity(StudyActivity::class.java, intent).setup()
        Screenshots.pumpUntil("экран объяснился") {
            studyText().contains("Нет сети") || buttons().isNotEmpty()
        }
        assertTrue("без сети и без партии экран промолчал:\n${studyText()}",
            studyText().contains("Нет сети"))
    }

    @Test
    fun network_dies_after_the_first_answer() {
        openStudy()
        click("Знаю"); click("К следующему слову")
        netOff()
        click("Знаю"); click("К следующему слову")
        click("Не знаю"); click("Дальше")
        assertTrue("плашки офлайна нет:\n${studyText()}", studyText().contains("Офлайн"))
    }

    @Test
    fun taking_back_a_know_without_network_keeps_the_counters_honest() {
        openStudy()
        netOff()
        click("Знаю")
        click("все-таки не знаю")      // возврат к вопросу, ответ исправлен
        click("Знаю"); click("К следующему слову")
        click("Знаю"); click("К следующему слову")
    }

    @Test
    fun network_dies_while_statistics_is_open() {
        openStudy()
        click("Знаю"); click("К следующему слову")
        openStats(); checkStatsSettled("с сетью")
        netOff()
        stats!!.get().refreshForTest()
        checkStatsSettled("сеть пропала на экране статистики")
        backFromStats()
        click("Знаю"); click("К следующему слову")
    }

    @Test
    fun statistics_opened_twice_without_network_does_not_pile_up() {
        openStudy()
        click("Знаю"); click("К следующему слову")
        openStats(); checkStatsSettled("первый заход с сетью")
        backFromStats()
        netOff()
        openStats(); checkStatsSettled("второй заход без сети")
        backFromStats()
        openStats(); checkStatsSettled("третий заход без сети")
        backFromStats()
        // Экран слова после всего этого обязан остаться рабочим.
        click("Знаю"); click("К следующему слову")
    }

    @Test
    fun network_returns_between_answers() {
        openStudy()
        netOff()
        click("Знаю"); click("К следующему слову")
        netOn()
        click("Знаю"); click("К следующему слову")
        Screenshots.pumpUntil("накопленное ушло на сервер") {
            OfflineCache.pendingCount() == 0
        }
        // Возврат в онлайн происходит на переходе к следующему слову — значит,
        // нужен ещё один ответ после того, как очередь опустела.
        click("Знаю"); click("К следующему слову")
        Screenshots.pumpUntil("экран вернулся в онлайн") { !studyText().contains("Офлайн") }
    }

    @Test
    fun network_returns_while_statistics_is_open() {
        openStudy()
        netOff()
        click("Знаю"); click("К следующему слову")
        openStats(); checkStatsSettled("статистика без сети")
        netOn()
        stats!!.get().refreshForTest()
        checkStatsSettled("статистика после возвращения связи")
        assertTrue("после возвращения связи числа не пришли:\n${statsText()}",
            statsText().contains("Знаю"))
    }

    @Test
    fun a_long_offline_round_keeps_counters_consistent_to_the_end() {
        openStudy()
        netOff()
        // Проходим круг целиком: именно так и было в самолёте.
        repeat(5) {
            if (buttons().any { b -> b.text.contains("Знаю") }) {
                click("Знаю")
                if (buttons().any { b -> b.text.contains("К следующему") }) click("К следующему слову")
            }
        }
        val t = studyText()
        assertTrue("после круга экран ничего не говорит:\n$t",
            t.contains("Офлайн") || t.contains("пройдена") || t.contains("в сессии"))
    }

    @Test
    fun restarting_the_round_without_network_does_not_break_the_counters() {
        openStudy()
        netOff()
        click("Знаю"); click("К следующему слову")
        click("Знаю"); click("К следующему слову")
        resetRound()
        study().refreshForTest()        // «Обновить» — тот же путь, что и перезапуск
        Screenshots.pumpUntil("экран ожил после обновления") { buttons().isNotEmpty() }
        checkCounters("после обновления без сети")
    }
}
