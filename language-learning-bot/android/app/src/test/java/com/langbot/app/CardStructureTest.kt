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
        // Экран обязан быть разрушен. Оставленный живым, он ломает соседние
        // проверки в общем прогоне: Robolectric держит состояние между
        // тестами, и ConnectionNoticeDoesNotShiftTheCardTest начал падать на
        // «карточка уехала вниз на 8» — в одиночку проходя трижды подряд. В
        // ReceiveMessagesToggleTest про этот капкан написано прямо, здесь его
        // просто не было.
        controller?.let { runCatching { it.pause().stop().destroy() } }
        controller = null
        runCatching { server.shutdown() }
    }

    private var controller:
        org.robolectric.android.controller.ActivityController<StudyActivity>? = null

    private fun open(fixture: String): StudyActivity {
        val file = File("src/test/resources/cards/$fixture.json")
        assertTrue("нет фикстуры $fixture — сначала make_card_fixtures.py", file.exists())
        cardJson = file.readText()
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1")
            .putExtra("language_name", "Иврит")
        val c = Robolectric.buildActivity(StudyActivity::class.java, intent).setup()
        controller = c
        val activity = c.get()
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

        // Четыре колонки: номер в частотном словаре, перевод, слово, транскрипция.
        // Номер без «#»: в узкой колонке он занимал место, из-за которого «1105»
        // переносилось на две строки.
        assertTrue("нет номера в словаре: $cells", cells.any { it == "40" })
        assertTrue("«#» из номера не убран: $cells", cells.none { it.startsWith("#") })
        assertTrue("нет перевода: $cells", cells.any { it == "один" })
        assertTrue("нет транскрипции: $cells", cells.any { it == "[ʔeˈχad]" })
        assertTrue("нет слова на иврите: $cells", cells.any { it.contains("אֶחָד") })
        assertTrue("нет подписи группы: $cells", cells.any { it.contains("Числительные") })

        // Слово стоит перед транскрипцией: читают его, транскрипция уточняет.
        val order = Screenshots.texts(extras(a)).map { it.text.toString() }
        assertTrue("слово должно идти перед транскрипцией: $order",
            order.indexOfFirst { it.contains("אֶחָד") } < order.indexOf("[ʔeˈχad]"))

        // Порядок задан в определениях тегов вручную — частотный список к нему
        // безразличен: «один» стоит 40-м, «девять» 5862-м.
        val ranks = cells.mapNotNull { it.toIntOrNull() }
        assertEquals("порядок строк не тот: $ranks", listOf(40, 1105, 417, 5862), ranks)

        // Своё слово выделено жирным: в списке из двадцати одного числительного
        // иначе его не найти.
        val own = Screenshots.texts(extras(a)).filter { it.text.toString() == "три (ж)" }
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

    @Test
    fun reading_examples_are_rendered_with_the_translation_on_its_own_line() {
        /*
         * Блок нового типа. В клиентах есть свойство, которое уже один раз
         * стоило показа: тип без своей ветки отрисовки молча исчезает —
         * исключения нет, в логе ничего, на экране пусто. Так пропадали
         * запрещённые дистракторы.
         *
         * Второе утверждение — про вёрстку. Владелец просил перевод СЛЕДУЮЩЕЙ
         * строкой, а не рядом с текстом, и строки с ивритом и русским должны
         * прижиматься к разным краям: иначе колонки не читаются.
         */
        val a = open("reading_niqqud")
        val клетки = Screenshots.texts(extras(a))
        val тексты = клетки.map { it.text.toString() }
        assertTrue("предложение не отрисовано: $тексты", тексты.any { it == "יש זמן" })
        assertTrue("перевод не отрисован: $тексты", тексты.any { it == "Время есть." })

        val предложение = клетки.first { it.text.toString() == "יש זמן" }
        val перевод = клетки.first { it.text.toString() == "Время есть." }
        val местоП = IntArray(2).also { предложение.getLocationOnScreen(it) }
        val местоР = IntArray(2).also { перевод.getLocationOnScreen(it) }
        assertTrue("перевод должен стоять НИЖЕ предложения, а не рядом",
            местоР[1] > местоП[1])
        // Сверяем РЕЗУЛЬТАТ раскладки, а не выставленный атрибут: Robolectric
        // не возвращает установленный textDirection — у всех ячеек выходит 1.
        // Об этом предупреждает соседняя проверка про колонки, и я на это
        // наступил. getParagraphDirection: 1 — слева направо, -1 — справа.
        assertEquals("ивритская строка должна раскладываться справа налево",
            -1, предложение.layout.getParagraphDirection(0))
        assertEquals("русская строка должна раскладываться слева направо",
            1, перевод.layout.getParagraphDirection(0))
    }

    @Test
    fun the_niqqud_icon_switches_the_word_and_the_big_word_together() {
        /*
         * Владелец: «огласовка включается по простому нажатию, без переходов
         * на другой экран». Нажатие по блоку карточки занято увеличением,
         * поэтому переключает отдельный значок рядом со словом.
         *
         * Крупное написание едет вместе с обычным: иначе на одном экране
         * окажутся две разные записи одного слова — это и было бы дефектом,
         * ради которого проверка написана.
         */
        val a = open("reading_niqqud")
        val содержимое = a.findViewById<ViewGroup>(R.id.cardContent)
        val слово = Screenshots.texts(содержимое).first { it.text.toString() == "זמן" }
        val значок = Screenshots.texts(содержимое).firstOrNull { it.text.toString() == "🔤" }
        assertTrue("значка переключения огласовки на карточке нет", значок != null)

        значок!!.performClick()
        assertEquals("после нажатия должна показаться огласованная форма",
            "זְמַן", слово.text.toString())
        значок.performClick()
        assertEquals("повторное нажатие должно вернуть упрощённую форму",
            "זמן", слово.text.toString())
    }
}
