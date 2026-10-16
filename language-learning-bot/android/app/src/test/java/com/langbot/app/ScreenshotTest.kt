package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * Рисует экраны в PNG и сверяет оформление с эталоном — без эмулятора.
 *
 * Что здесь проверяется
 * ---------------------
 * 1. Экран вообще рисуется (не белый лист).
 * 2. Механика вёрстки: обрезанный текст, нулевой размер, выход за правый край.
 * 3. Оформление совпадает с эталоном — то есть вёрстка не съехала.
 *
 * Чего здесь НЕ проверяется: правильность содержимого. «1 ошибок» вместо
 * «1 ошибка» такой тест пропустит — эталон снимут с ошибкой, и она станет
 * нормой. Содержимое проверяет человек, глядя на картинки в build/screenshots,
 * и структурные утверждения в CardStructureTest.
 *
 * Карточки берутся из фикстур, снятых настоящим card_builder
 * (resources/make_card_fixtures.py). Слова в них заморожены, поэтому любое
 * расхождение пикселей означает изменение оформления, а не словаря.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w411dp-h891dp-xhdpi")
class ScreenshotTest {

    private lateinit var server: MockWebServer
    private var cardJson: String = "{}"
    private val fixturesDir = File("src/test/resources/cards")

    private val problems = mutableListOf<String>()

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        Screenshots.outDir.mkdirs()

        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                val body = when {
                    path.startsWith("/session/") -> """{"session_id":"sid-1","card":$cardJson}"""
                    path.startsWith("/languages") -> LANGUAGES
                    path.startsWith("/settings/") -> SETTINGS
                    path.contains("chart_manifest") -> CHART_MANIFEST
                    path.startsWith("/statistics/") -> STATISTICS
                    path.startsWith("/version") -> VERSION
                    else -> null
                }
                return if (body == null) MockResponse().setResponseCode(404)
                else MockResponse().setResponseCode(200).setBody(body)
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    /** Снять вид, проверить непустоту, вёрстку и совпадение с эталоном. */
    private fun shoot(view: View, name: String) {
        val bmp = Screenshots.render(view)
        Screenshots.write(bmp, File(Screenshots.outDir, "$name.png"))

        val painted = Screenshots.paintedRatio(bmp)
        if (painted < 0.005) {
            // Первая версия этого теста сняла голый заголовок и осталась
            // зелёной — проверка «хоть что-то нарисовано» стоит именно здесь.
            problems += "$name: экран пуст (закрашено ${"%.2f".format(painted * 100)}%)"
            return
        }
        Screenshots.layoutProblems(view, bmp.width).forEach { problems += "$name: $it" }
        Screenshots.checkBaseline(name, bmp)?.let { problems += "$name: $it" }
    }

    private fun studyWith(fixture: File): StudyActivity {
        cardJson = fixture.readText()
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1")
            .putExtra("language_name", "Иврит")
        val activity = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        Screenshots.pumpUntil("${fixture.nameWithoutExtension}: карточка отрисована") {
            activity.findViewById<ViewGroup>(R.id.cardContent).childCount > 0 ||
                activity.findViewById<ViewGroup>(R.id.buttonRow).childCount > 0
        }
        return activity
    }

    @Test
    fun card_states_match_their_baselines() {
        val fixtures = fixturesDir.listFiles { f -> f.name.endsWith(".json") }
            ?.sortedBy { it.name } ?: emptyList()
        assertTrue(
            "нет фикстур в ${fixturesDir.absolutePath} — сначала make_card_fixtures.py",
            fixtures.isNotEmpty(),
        )

        for (fixture in fixtures) {
            val activity = studyWith(fixture)
            shoot(Screenshots.scrollColumnOrRoot(activity, R.id.swipeRefresh), fixture.nameWithoutExtension)
            activity.finish()
        }
        report()
    }

    @Test
    fun other_key_screens_match_their_baselines() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()

        val languages = Robolectric.buildActivity(LanguagesActivity::class.java).setup().get()
        // Ждём строки в САМОМ списке. Прежнее условие считало любые тексты на
        // экране, а их хватает уже от заголовка в шапке: снимок иногда делался,
        // пока список пуст, и тест падал «экран пуст» через раз.
        Screenshots.pumpUntil("список языков загружен") {
            languages.findViewById<ViewGroup>(R.id.recycler).childCount > 0
        }
        // Снимаем список, а не весь экран: в шапке ActionBar стоит подпись
        // «v4.2.0», и эталон разъезжался бы при КАЖДОМ поднятии версии. Такой
        // эталон приучает пересматривать картинки не глядя, то есть отменяет
        // сам себя.
        shoot(languages.findViewById(R.id.recycler), "screen_languages")
        languages.finish()

        val settingsIntent = Intent(ctx, SettingsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val settings = Robolectric.buildActivity(SettingsActivity::class.java, settingsIntent).setup().get()
        Screenshots.pumpUntil("настройки загружены") {
            Screenshots.texts(settings.findViewById(android.R.id.content)).size > 3
        }
        shoot(Screenshots.contentColumn(settings), "screen_settings")
        settings.finish()

        val statsIntent = Intent(ctx, StatsActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val stats = Robolectric.buildActivity(StatsActivity::class.java, statsIntent).setup().get()
        // Ждём не «появились надписи», а что ДОГОВОРИЛ блок графиков. Сводка и
        // графики теперь грузятся порознь, и по одному лишь наличию надписей
        // снимок делался на полпути: сводка уже есть, под заголовком «Графики»
        // ещё пусто — эталон расходился с собой через раз.
        Screenshots.pumpUntil("статистика загружена") {
            val texts = Screenshots.texts(stats.findViewById(android.R.id.content))
            texts.size > 3 && texts.any {
                val t = it.text.toString()
                t.contains("Нет данных для графиков") || t.contains("Не удалось")
            }
        }
        shoot(Screenshots.contentColumn(stats), "screen_stats")
        stats.finish()

        report()
    }

    private fun report() {
        assertTrue(problems.joinToString("\n", prefix = "\n"), problems.isEmpty())
    }

    companion object {
        private const val LANGUAGES = """
        [{"id":"lang-1","name_ru":"Иврит","name_foreign":"עברית"},
         {"id":"lang-2","name_ru":"Китайский","name_foreign":"中文"}]"""

        private const val SETTINGS = """
        {"start_word":1,"skip_marked":false,"use_check_date":true,"show_check_date":true,
         "show_big":false,"show_sounds":true,"show_tones":true,"show_references":true,
         "show_radicals":false,"show_skip_button":true,"show_tags":true,"show_hint_meaning":true,
         "show_hint_phoneticassociation":true,"show_hint_phoneticsound":false,
         "show_hint_writing":false,"random_pick_mode":true,"random_sound":true,
         "random_transcription":true,"quiz_options_count":4,"unknown_limit_new_words":10,
         "max_check_interval":90,"reset_same_day_hours":4,"day_start_hour":4,"timezone":"Europe/Rome"}"""

        // progress_percentage сервер считает как words_known / total_words
        // (statistics_repository), поэтому число здесь обязано сходиться с
        // остальными: 410 / 9995 = 4.1. С несогласованными числами эталон
        // выглядел бы так, будто клиент считает процент неправильно.
        private const val STATISTICS = """
        {"words_studied":523,"words_known":410,"words_skipped":12,"words_unknown":101,
         "total_words":9995,"words_for_today":10,"progress_percentage":4.1}"""

        private const val CHART_MANIFEST = """{"sections":[],"captions":{}}"""

        private const val VERSION = """{"version":"4.1.1","version_code":40101}"""
    }
}
