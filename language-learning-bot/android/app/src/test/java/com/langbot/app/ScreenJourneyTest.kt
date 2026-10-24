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
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.ParameterizedRobolectricTestRunner
import org.robolectric.android.controller.ActivityController
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * Сквозные пути по экранам, и связь рвётся в каждой их точке.
 *
 * Просьба владельца: проверять не переходы внутри одного экрана, а дороги вроде
 * «выбор языка → слово → знаю → ответ → ой не знаю → следующее слово →
 * статистика из меню → назад → выбор языка → настройки → назад → слово», и
 * «сеть может пропасть и вернуться в любой точке такой дороги».
 *
 * Поэтому здесь дорога задаётся списком шагов, а проверка порождается на
 * КАЖДУЮ точку обрыва: шаг номер N проходит без сети, а ещё через два шага
 * связь возвращается. После каждого шага — те же утверждения, что и в
 * OfflineMatrixTest: счётчики сходятся, экран не молчит, ничего не двоится.
 *
 * Вход, подсказки и помощь сюда не входят по решению владельца: вход без сети
 * бессмыслен, а помощь не критична.
 */
@RunWith(ParameterizedRobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class ScreenJourneyTest(
    private val name: String,
    private val journey: List<String>,
    private val dropAt: Int,
) {

    companion object {
        /** Дорога владельца: язык → слово → ответы → статистика → настройки → слово. */
        private val FULL = listOf(
            "languages", "study", "know", "next", "dont_know", "next",
            "stats", "back", "know", "next", "languages", "settings", "back", "study",
        )

        /** Короткая дорога вокруг «ой, все-таки не знаю». */
        private val TAKE_BACK = listOf(
            "study", "know", "reconsider", "know", "next", "stats", "back", "know", "next",
        )

        /** Хождение между статистикой и словом — на нём приложение падало. */
        private val BACK_AND_FORTH = listOf(
            "study", "know", "next", "stats", "back", "stats", "back", "stats", "back", "know",
        )

        @JvmStatic
        @ParameterizedRobolectricTestRunner.Parameters(name = "{0}, обрыв перед шагом {2}")
        fun data(): List<Array<Any>> {
            val out = mutableListOf<Array<Any>>()
            for ((title, steps) in listOf(
                "дорога владельца" to FULL,
                "ой, все-таки не знаю" to TAKE_BACK,
                "туда-сюда в статистику" to BACK_AND_FORTH,
            )) {
                // -1 — вся дорога со связью: опора, с которой сравнивать.
                out += arrayOf<Any>(title, steps, -1)
                steps.indices.forEach { i -> out += arrayOf<Any>(title, steps, i) }
            }
            return out
        }
    }

    private lateinit var bls: FakeBls
    private var study: ActivityController<StudyActivity>? = null
    private var stats: ActivityController<StatsActivity>? = null
    private var settings: ActivityController<SettingsActivity>? = null
    private var languages: ActivityController<LanguagesActivity>? = null
    private var lastDone = 0

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx); ChartCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        File(ctx.filesDir, "charts").deleteRecursively()
        UserPrefs.saveUserId(ctx, "user-1")
        bls = FakeBls(); bls.start(); BLSClient.init(bls.url())
    }

    @After
    fun tearDown() {
        listOf(study, stats, settings, languages).forEach { c ->
            c?.let { runCatching { it.pause().stop().destroy() } }
        }
        bls.shutdown()
    }

    // ── чтение экрана ────────────────────────────────────────────────────

    private fun visibleText(root: View?, skip: Int = 0): String {
        if (root == null) return ""
        val sb = StringBuilder()
        fun walk(v: View) {
            if (v.visibility != View.VISIBLE) return
            if (skip != 0 && v.id == skip) return
            if (v is TextView) sb.append(v.text).append('\n')
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return sb.toString()
    }

    private fun <T : View> collect(root: View?, type: Class<T>): List<T> {
        if (root == null) return emptyList()
        val out = mutableListOf<T>()
        fun walk(v: View) {
            if (type.isInstance(v)) out.add(type.cast(v)!!)
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return out
    }

    private fun studyRoot(): View? = study?.get()?.findViewById(R.id.swipeRefresh)
    private fun statsRoot(): View? = stats?.get()?.findViewById(R.id.statsContainer)
    private fun buttons(): List<MaterialButton> =
        collect(study?.get()?.findViewById(R.id.buttonRow), MaterialButton::class.java) +
        collect(study?.get()?.findViewById(R.id.banButtonRow), MaterialButton::class.java)

    // ── шаги ─────────────────────────────────────────────────────────────

    private fun intent(cls: Class<*>) =
        Intent(ApplicationProvider.getApplicationContext(), cls)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")

    private fun step(name: String) {
        when (name) {
            "languages" -> {
                languages?.let { runCatching { it.pause().stop().destroy() } }
                languages = Robolectric.buildActivity(
                    LanguagesActivity::class.java, intent(LanguagesActivity::class.java)).setup()
                Screenshots.pumpUntil("список языков показан", timeoutMs = 25_000) {
                    visibleText(languages?.get()?.findViewById(android.R.id.content)).isNotBlank()
                }
            }
            "study" -> {
                study?.let { runCatching { it.pause().stop().destroy() } }
                study = Robolectric.buildActivity(
                    StudyActivity::class.java, intent(StudyActivity::class.java)).setup()
                waitForStudy()
            }
            "stats" -> {
                stats = Robolectric.buildActivity(
                    StatsActivity::class.java, intent(StatsActivity::class.java)).setup()
                waitStatsSettled()
            }
            "settings" -> {
                settings = Robolectric.buildActivity(
                    SettingsActivity::class.java, intent(SettingsActivity::class.java)).setup()
                Screenshots.pumpUntil("настройки что-то показали", timeoutMs = 25_000) {
                    visibleText(settings?.get()?.findViewById(R.id.settingsContainer)).isNotBlank()
                }
            }
            "back" -> {
                when {
                    stats != null -> { stats!!.pause().stop().destroy(); stats = null }
                    settings != null -> { settings!!.pause().stop().destroy(); settings = null }
                }
                study?.let { it.start().resume() }
            }
            "know" -> tap("Знаю")
            "dont_know" -> tap("Не знаю")
            "next" -> if (!tap("К следующему слову")) tap("Дальше")
            "reconsider" -> tap("все-таки не знаю")
            else -> throw IllegalArgumentException("неизвестный шаг $name")
        }
        checkAll("шаг «$name»")
    }

    private fun waitForStudy() {
        runCatching {
            Screenshots.pumpUntil("экран слова ответил", timeoutMs = 25_000) {
                buttons().isNotEmpty() || visibleText(studyRoot()).contains("Нет сети") ||
                    visibleText(studyRoot()).contains("повторено") ||
                    visibleText(studyRoot()).contains("пройдена")
            }
        }
    }

    private fun waitStatsSettled() {
        runCatching {
            Screenshots.pumpUntil("статистика договорила", timeoutMs = 25_000) {
                val t = visibleText(statsRoot())
                collect(statsRoot(), ProgressBar::class.java).isEmpty() &&
                    (collect(statsRoot(), ImageView::class.java).any { it.drawable is BitmapDrawable } ||
                        t.contains("Знаю") || t.contains("Нет связи") || t.contains("Связи нет") ||
                        t.contains("с прошлого раза") || t.contains("Нет данных") ||
                        t.contains("Не хватило памяти"))
            }
        }
    }

    /** Нажать кнопку, если она есть; дождаться, пока экран ответит. */
    private fun tap(contains: String): Boolean {
        val btn = buttons().firstOrNull { it.text.contains(contains) } ?: return false
        // Плашку «соединение нестабильно» из снимка исключаем: иначе ожидание
        // кончается на ней, пока нажатие ещё висит в сети.
        val snapshot = { buttons().map { it.text.toString() } to
            visibleText(studyRoot(), skip = R.id.restartNotice) }
        val before = snapshot()
        btn.performClick()
        runCatching {
            Screenshots.pumpUntil("экран ответил на «$contains»", timeoutMs = 25_000) {
                snapshot() != before
            }
        }
        return true
    }

    // ── утверждения ──────────────────────────────────────────────────────

    private fun num(re: Regex, t: String) = re.find(t)?.groupValues?.get(1)?.toIntOrNull()

    private fun checkAll(where: String) {
        val t = visibleText(studyRoot())
        val correct = num(Regex("(\\d+) правильн"), t) ?: 0
        val wrong = num(Regex("(\\d+) ошиб"), t) ?: 0
        val done = num(Regex("готово (\\d+) из"), t)
        val barTotal = num(Regex("готово \\d+ из (\\d+)"), t)
        val pos = num(Regex("в сессии: (\\d+) из"), t)
        val total = num(Regex("в сессии: \\d+ из (\\d+)"), t)
        if (done != null) {
            assertTrue("$where: готово ($done) ≠ правильные ($correct) + ошибки ($wrong)\n$t",
                done == correct + wrong)
            if (barTotal != null)
                assertTrue("$where: готово ($done) больше круга ($barTotal)\n$t", done <= barTotal)
            assertTrue("$where: «готово» убыло с $lastDone до $done\n$t", done >= lastDone)
            lastDone = done
        }
        if (pos != null && total != null)
            assertTrue("$where: позиция ($pos) обогнала круг ($total)\n$t", pos <= total)

        val st = visibleText(statsRoot())
        if (st.isNotBlank())
            assertTrue("$where: разделы графиков задвоились\n$st",
                Regex("Графики").findAll(st).count() <= 1)
    }

    // ── сама проверка ────────────────────────────────────────────────────

    @Test
    fun the_journey_survives_the_outage() {
        journey.forEachIndexed { i, s ->
            if (i == dropAt) bls.online = false
            if (dropAt >= 0 && i == dropAt + 2) bls.online = true
            step(s)
        }
        // Экран слова обязан остаться живым: либо карточка, либо внятное слово.
        val t = visibleText(studyRoot())
        if (study != null) {
            assertTrue("дорога кончилась немым экраном: [$t]",
                buttons().isNotEmpty() || t.contains("Нет сети") || t.contains("повторено") ||
                    t.contains("пройдена") || t.contains("Офлайн"))
        }
    }
}
