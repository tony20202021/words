package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
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
 * Утверждения о разложенном дереве экрана — не о картинке.
 *
 * Зачем отдельно от снимков
 * -------------------------
 * Сверка с эталоном ловит «стало не так, как было», но молчит про «так было
 * неправильно с самого начала»: неверную вёрстку просто снимут в эталон, и она
 * станет нормой. Ещё эталон падает от любой мелочи — другой шрифт, другая
 * версия SDK.
 *
 * Здесь наоборот: проверяется смысл вёрстки, а не пиксели. Ивритская колонка
 * обязана быть справа налево и крупнее русской; в пик-режиме обязана быть ровно
 * одна кнопка; у таблицы огласовок обязано быть столько строк, сколько
 * вариантов. Это переживает смену шрифта и падает только тогда, когда сломали
 * именно то, ради чего вёрстку делали.
 *
 * Карточки — те же фикстуры настоящего card_builder, что и у снимков.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w411dp-h891dp-xhdpi")
class CardStructureTest {

    private lateinit var server: MockWebServer
    private var cardJson: String = "{}"

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                return if ((request.path ?: "").startsWith("/session/")) {
                    MockResponse().setResponseCode(200)
                        .setBody("""{"session_id":"sid-1","card":$cardJson}""")
                } else MockResponse().setResponseCode(404)
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    private fun open(fixture: String): StudyActivity {
        val file = File("src/test/resources/cards/$fixture.json")
        assertTrue("нет фикстуры $fixture — сначала make_card_fixtures.py", file.exists())
        cardJson = file.readText()
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1")
            .putExtra("language_name", "Иврит")
        val activity = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        Screenshots.pumpUntil("$fixture: карточка отрисована") {
            activity.findViewById<ViewGroup>(R.id.cardContent).childCount > 0 ||
                activity.findViewById<ViewGroup>(R.id.buttonRow).childCount > 0
        }
        // Раскладываем как при съёмке, иначе размеры и направление ещё не
        // посчитаны и утверждения проверяли бы пустоту.
        Screenshots.render(Screenshots.scrollColumnOrRoot(activity, R.id.swipeRefresh))
        return activity
    }

    private fun buttonTexts(a: StudyActivity): List<String> =
        Screenshots.texts(a.findViewById<ViewGroup>(R.id.buttonRow)).map { it.text.toString() } +
            Screenshots.texts(a.findViewById<ViewGroup>(R.id.banButtonRow)).map { it.text.toString() }

    private fun extras(a: StudyActivity): ViewGroup = a.findViewById(R.id.extraCardsArea)

    @Test
    fun pick_mode_offers_options_and_only_the_dont_know_button() {
        val a = open("pick_mode")
        // Варианты рисуются в тот же buttonRow, что и кнопки, — поэтому считаем
        // не «сколько всего», а «что именно» осталось сверх вариантов.
        val all = buttonTexts(a)
        val optionTexts = listOf("עִם", "אֲבָל", "כְּמוֹ", "בִּשְׁבִיל")
        optionTexts.forEach { opt ->
            assertTrue("вариант «$opt» не отрисован: $all", all.any { it.contains(opt) })
        }

        val controls = all.filterNot { text -> optionTexts.any { text.contains(it) } }
        // Вместе с вариантами полагается ровно одна кнопка — «Не знаю».
        // «Пропускать» здесь была бы лишней: она про экран ответа.
        assertEquals("сверх вариантов должна остаться одна кнопка: $controls", 1, controls.size)
        assertTrue("ожидалась «Не знаю», а не $controls", controls.single().contains("Не знаю"))
        assertTrue("«Пропускать» в пик-режиме не место: $controls",
            controls.none { it.contains("Пропускать") })
    }

    @Test
    fun after_a_pick_answer_the_ban_button_appears() {
        val a = open("pick_after_answer")
        val buttons = buttonTexts(a)
        assertTrue(
            "после ответа в пик-режиме нужна кнопка запрета комбинации, есть: $buttons",
            buttons.any { it.contains("комбинаци", ignoreCase = true) },
        )
        assertTrue("нужна кнопка «Пропускать»: $buttons", buttons.any { it.contains("Пропускать") })
    }

    @Test
    fun hebrew_column_is_right_to_left_and_larger_than_the_russian_one() {
        val a = open("answer_hebrew")
        val cells = Screenshots.texts(extras(a))
        assertTrue("блоки доп. информации пусты", cells.size >= 4)

        val hebrew = cells.filter { it.text.any { ch -> ch in '֐'..'׿' } }
        val russian = cells.filter { it.text.any { ch -> ch in 'а'..'я' } && it.text.none { ch -> ch in '֐'..'׿' } }
        assertTrue("не нашли ивритских ячеек", hebrew.isNotEmpty())
        assertTrue("не нашли русских ячеек", russian.isNotEmpty())

        // Проверяем РЕЗУЛЬТАТ раскладки, а не выставленный атрибут: сперва я
        // сравнивал textDirection и получил 1 у всех ячеек — Robolectric не
        // возвращает установленное значение. Да и дефект был именно в том, ЧТО
        // получилось: направление абзаца берётся по первому сильному символу, и
        // строка «אוֹתוֹ [ʔoˈto]» утягивала вправо весь блок.
        //   getParagraphDirection: 1 — слева направо, -1 — справа налево.
        hebrew.forEach {
            assertEquals(
                "ивритская ячейка «${it.text}» должна раскладываться справа налево",
                -1, it.layout.getParagraphDirection(0),
            )
        }
        russian.forEach {
            assertEquals(
                "русская ячейка «${it.text}» должна раскладываться слева направо",
                1, it.layout.getParagraphDirection(0),
            )
        }

        // Огласовка — мелкие знаки под буквами; в одном кегле с русским её не
        // разглядеть, ради неё блок и заводился. Требуем крупный кегль именно
        // там, где огласовка есть: в заголовке стоит голое написание «עם», и
        // разглядывать в нём нечего.
        val vocalized = hebrew.filter { it.text.any { ch -> ch in '֑'..'ׇ' } }
        assertTrue("в блоках нет ни одной огласованной формы", vocalized.isNotEmpty())
        val maxRussian = russian.maxOf { it.textSize }
        vocalized.forEach {
            assertTrue(
                "огласованное «${it.text}» (${it.textSize}) должно быть крупнее русского ($maxRussian)",
                it.textSize > maxRussian,
            )
        }
    }

    @Test
    fun the_extras_table_has_a_header_row_and_one_row_per_variant() {
        val a = open("answer_hebrew")
        val cells = Screenshots.texts(extras(a)).map { it.text.toString() }

        // Заголовок разрезан на те же две колонки, что и строки: целиком он
        // начинается с ивритской буквы и уезжал вправо вместе с остальным.
        assertTrue("нет русской половины заголовка огласовок: $cells",
            cells.any { it.contains("вариантов огласовки") })
        assertTrue("нет русской половины заголовка однокоренных: $cells",
            cells.any { it.contains("слов с этой основой") })

        // Обе огласовки из фикстуры должны доехать до экрана.
        assertTrue("нет варианта «народ»: $cells", cells.any { it.contains("народ") })
        assertTrue("нет варианта «с, вместе с»: $cells", cells.any { it.contains("вместе с") })
    }

    @Test
    fun a_card_without_extras_shows_no_empty_blocks() {
        val a = open("no_extras")
        // Пустая рамка на месте отсутствующего блока — тоже дефект: место
        // занято, смысла нет.
        assertEquals(
            "у слова без огласовок и однокоренных не должно быть блоков",
            View.GONE, extras(a).visibility,
        )
    }

    @Test
    fun markup_characters_are_shown_as_text_not_as_tags() {
        val a = open("markup_chars")
        val all = Screenshots.texts(a.findViewById<ViewGroup>(R.id.cardContent))
            .joinToString(" ") { it.text.toString() }
        // Телеграм на этом уже спотыкался: «<» в переводе съедал карточку
        // целиком. В андроиде символы обязаны остаться символами.
        assertTrue("угловые скобки потерялись: $all", all.contains("<") && all.contains(">"))
        assertTrue("амперсанд потерялся: $all", all.contains("&"))
    }

    @Test
    fun the_counters_agree_with_the_numbers() {
        val a = open("counters_one")
        val texts = Screenshots.texts(a.findViewById<ViewGroup>(R.id.progressArea))
            .map { it.text.toString() }
        assertTrue("ожидалось «1 ошибка», есть: $texts", texts.any { it == "1 ошибка" })
        assertTrue("ожидалось «1 правильный», есть: $texts", texts.any { it == "1 правильный" })
    }

    @Test
    fun the_tag_group_shows_four_columns_and_marks_the_current_word() {
        val a = open("tag_group")
        val cells = Screenshots.texts(extras(a)).map { it.text.toString() }

        // Четыре колонки: номер в частотном словаре, перевод, транскрипция, слово.
        assertTrue("нет номера в словаре: $cells", cells.any { it == "#40" })
        assertTrue("нет перевода: $cells", cells.any { it == "один" })
        assertTrue("нет транскрипции: $cells", cells.any { it == "[ʔeˈχad]" })
        assertTrue("нет слова на иврите: $cells", cells.any { it.contains("אֶחָד") })
        assertTrue("нет подписи группы: $cells", cells.any { it.contains("Числительные") })

        // Порядок задан в определениях тегов вручную — частотный список к нему
        // безразличен: «один» стоит 40-м, «десять» 890-м.
        val ranks = cells.filter { it.startsWith("#") }.mapNotNull { it.drop(1).toIntOrNull() }
        assertEquals("порядок строк не тот: $ranks", listOf(40, 130, 417, 890), ranks)

        // Своё слово выделено жирным: в списке из двадцати одного числительного
        // иначе его не найти.
        val own = Screenshots.texts(extras(a)).filter { it.text.toString() == "три" }
        assertTrue("строки текущего слова нет", own.isNotEmpty())
        assertTrue("текущее слово должно быть выделено",
            own.all { it.typeface?.isBold == true })
    }

    @Test
    fun every_question_variant_shows_its_own_modality() {
        // У каждого варианта вопроса своя подпись, и перепутать их — значит
        // показать учащемуся ответ. Проверяем, что показано именно ожидаемое.
        val expected = mapOf(
            "question_foreign" to "Слово на иностранном",
            "question_translation" to "Слово на русском",
            "question_transcription" to "Транскрипция",
            "question_sound" to "по звуку",
        )
        for ((fixture, label) in expected) {
            val a = open(fixture)
            val texts = Screenshots.texts(a.findViewById<ViewGroup>(R.id.cardContent))
                .joinToString(" ") { it.text.toString() }
            assertTrue("$fixture: ожидалась подпись «$label», есть: $texts", texts.contains(label))
            a.finish()
        }
    }
}
