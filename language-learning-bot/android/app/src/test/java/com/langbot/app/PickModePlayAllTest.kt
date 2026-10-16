package com.langbot.app

import android.content.Intent
import android.os.Looper
import android.view.View
import android.widget.LinearLayout
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.google.gson.Gson
import com.langbot.app.network.BLSClient
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardItem
import com.langbot.app.network.CardMeta
import com.langbot.app.network.PickOption
import com.langbot.app.network.PickOptions
import com.langbot.app.network.SessionResponse
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import java.io.File

/**
 * Пик-режим по звуку: кнопка «проиграть все» и подсветка звучащего варианта.
 *
 * Просьба владельца: «много кнопок звуков — нужно добавить кнопку
 * "воспроизвести все", под кнопками воспроизведения каждого отдельного слова,
 * в одном ряду с кнопкой "не знаю"; при воспроизведении подсвечивать каждую
 * текущую кнопку как сейчас проигрывается».
 *
 * Почему проверяется именно РЯД, а не просто наличие кнопки: кнопка, стоящая
 * в общем столбце вариантов, читается как ещё один вариант ответа — её нажмут
 * вместо выбора. Место рядом с «Не знаю» и отделяет её от вариантов.
 */
@RunWith(RobolectricTestRunner::class)
class PickModePlayAllTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"
    private val gson = Gson()

    /** Сколько звуковых вариантов кладёт «сервер» в карточку. */
    private var optionCount = 3

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        File(ctx.filesDir, "sounds").deleteRecursively()
        UserPrefs.saveUserId(ctx, u)

        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return if (path.startsWith("/session/") && request.method == "GET") {
                    MockResponse().setResponseCode(200).setBody(
                        gson.toJson(SessionResponse(session_id = "sid-1", card = soundPickCard()))
                    )
                } else {
                    MockResponse().setResponseCode(404)
                }
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    private val dontKnow =
        CardButton("pick_dont_know", "❓ Не знаю", "outline-secondary", null,
                   "record_and_reveal", "dont_know")

    /** Вариант «по звуку»: в target_text лежат пути к файлам через «|». */
    private fun soundPickCard() = Card(
        show_answer = false,
        content = listOf(CardItem("translation", "книга")),
        buttons = listOf(dontKnow),
        meta = CardMeta(
            word_id = "w1", word_number = 1, session_pos = 1, session_total = 10,
            correct_count = 0, incorrect_count = 0, pending_result = null, score_badge = null,
        ),
        pick_options = PickOptions(
            target_modality = "sound",
            options = (1..optionCount).map {
                PickOption("w$it", "sounds/w$it-a.mp3|sounds/w$it-b.mp3", it == 1, null)
            },
        ),
    )

    private fun launchStudy(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", l)
            .putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        pumpUntil("карточка пик-режима по звуку отрисована") {
            buttons(a).any { it.text.contains("Выбрать") }
        }
        return a
    }

    private fun pumpUntil(what: String, timeoutMs: Long = 15_000, cond: () -> Boolean) {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) return
            Thread.sleep(10)
        }
        fail("не дождались: $what")
    }

    private fun buttons(a: StudyActivity): List<MaterialButton> {
        val out = mutableListOf<MaterialButton>()
        fun walk(v: View) {
            if (v is MaterialButton) out.add(v)
            if (v is LinearLayout) (0 until v.childCount).forEach { walk(v.getChildAt(it)) }
        }
        walk(a.findViewById<LinearLayout>(R.id.buttonRow))
        return out
    }

    /** Ряд, в котором лежит кнопка с таким текстом. */
    private fun rowOf(a: StudyActivity, contains: String): List<String>? {
        val root = a.findViewById<LinearLayout>(R.id.buttonRow)
        fun walk(v: View): List<String>? {
            if (v is LinearLayout) {
                val own = (0 until v.childCount).mapNotNull { v.getChildAt(it) as? MaterialButton }
                if (own.any { it.text.contains(contains) }) return own.map { it.text.toString() }
                for (i in 0 until v.childCount) walk(v.getChildAt(i))?.let { return it }
            }
            return null
        }
        return walk(root)
    }

    @Test
    fun `кнопка проиграть все появляется при нескольких вариантах`() {
        val a = launchStudy()
        val texts = buttons(a).map { it.text.toString() }
        assertTrue("кнопки «Все» нет, есть: $texts", texts.any { it.contains("Все") })
    }

    @Test
    fun `кнопка проиграть все стоит в одном ряду с Не знаю`() {
        val a = launchStudy()
        val row = rowOf(a, "Все")
        assertTrue("«Все» и «Не знаю» в разных рядах: ряд «Все» = $row",
                   row != null && row.any { it.contains("Не знаю") })
    }

    @Test
    fun `при одном варианте проигрывать все нечего`() {
        optionCount = 1
        val a = launchStudy()
        val texts = buttons(a).map { it.text.toString() }
        assertFalse("кнопка «Все» на единственном варианте: $texts",
                    texts.any { it.contains("Все") })
        assertTrue("«Не знаю» пропала: $texts", texts.any { it.contains("Не знаю") })
    }

    @Test
    fun `варианты и выбор остаются на месте`() {
        val a = launchStudy()
        val texts = buttons(a).map { it.text.toString() }
        assertEquals("кнопок прослушивания не столько, сколько вариантов: $texts",
                     optionCount, texts.count { it.contains("🔊") })
        assertEquals("кнопок выбора не столько, сколько вариантов: $texts",
                     optionCount, texts.count { it.contains("Выбрать") })
    }

    @Test
    fun `звучащий вариант видно на кнопке`() {
        val a = launchStudy()
        val listen = buttons(a).filter { it.text.contains("🔊") }
        a.markPlayingForTest(1)
        assertEquals("подсветка не встала на звучащий вариант: " +
            "${listen.map { it.text }}", "🔈 2", listen[1].text.toString())
        assertTrue("соседние кнопки тоже подсвечены: ${listen.map { it.text }}",
                   listen[0].text.contains("▶") && listen[2].text.contains("▶"))

        // Звук кончился — отметка снимается, иначе на экране вечно «играет».
        a.markPlayingForTest(null)
        assertFalse("подсветка осталась после конца звука: ${listen.map { it.text }}",
                    listen.any { it.text.contains("🔈") })
    }

    @Test
    fun `прослушанный вариант отличается от звучащего`() {
        val a = launchStudy()
        val listen = buttons(a).filter { it.text.contains("🔊") }
        listen[0].performClick()          // прослушали первый
        shadowOf(Looper.getMainLooper()).idle()
        a.markPlayingForTest(null)        // звук доиграл
        assertEquals("прослушанный вариант не отмечен: ${listen.map { it.text }}",
                     "🔊 1", listen[0].text.toString())
    }
}

/**
 * Паузы при проигрывании подряд.
 *
 * Просьба владельца после первой версии «▶ Все»: «сделать чуть больше паузу
 * между разными строками». Внутри одного варианта файлы — это одно и то же
 * слово разными голосами, их дробить незачем; а вот варианты между собой без
 * заметной паузы сливаются в поток, и сравнивать становится нечего.
 */
class PlaybackGapTest {

    @org.junit.Test
    fun `между голосами одного варианта пауза короткая`() {
        org.junit.Assert.assertEquals(
            StudyActivity.BETWEEN_FILES_MS, StudyActivity.gapBefore(next = 1, after = 1))
    }

    @org.junit.Test
    fun `между разными вариантами пауза длиннее`() {
        org.junit.Assert.assertEquals(
            StudyActivity.BETWEEN_OPTIONS_MS, StudyActivity.gapBefore(next = 2, after = 1))
        org.junit.Assert.assertTrue(
            "пауза между вариантами не длиннее, чем внутри варианта",
            StudyActivity.BETWEEN_OPTIONS_MS > StudyActivity.BETWEEN_FILES_MS)
    }

    @org.junit.Test
    fun `вне пик-режима пауза остаётся прежней`() {
        // Кнопки звука на обычной карточке вариантов не знают: у них option = null,
        // и удлинять паузу между ними не за что.
        org.junit.Assert.assertEquals(
            StudyActivity.BETWEEN_FILES_MS, StudyActivity.gapBefore(next = null, after = null))
    }
}

/**
 * Подсветок на экране должно быть не больше одной.
 *
 * Жалоба владельца: «нажал 1 строку — кнопка осталась подкрашенной, норм;
 * нажал воспроизвести все — стало меняться текущее выделение, но при этом ещё
 * осталась подкраска от первого нажатия».
 *
 * Отметки две, и они про разное: «прослушан» держится долго и отвечает на
 * вопрос «что я слушал отдельно», «звучит сейчас» живёт, пока идёт звук. После
 * «▶ Все» первая теряет смысл — слушали всё, — и остаётся на экране просто
 * мешать.
 */
@RunWith(RobolectricTestRunner::class)
class PlayAllClearsThePlayedMarkTest {

    private lateinit var server: MockWebServer
    private val gson = Gson()

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        UserPrefs.saveUserId(ctx, "user-1")
        server = MockWebServer()
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                val path = request.path ?: ""
                return if (path.startsWith("/session/") && request.method == "GET") {
                    MockResponse().setResponseCode(200).setBody(gson.toJson(
                        SessionResponse(session_id = "sid-1", card = Card(
                            show_answer = false,
                            content = listOf(CardItem("translation", "книга")),
                            buttons = listOf(CardButton("pick_dont_know", "❓ Не знаю",
                                "outline-secondary", null, "record_and_reveal", "dont_know")),
                            meta = CardMeta(word_id = "w1", word_number = 1, session_pos = 1,
                                session_total = 10, correct_count = 0, incorrect_count = 0,
                                pending_result = null, score_badge = null),
                            pick_options = PickOptions(
                                target_modality = "sound",
                                options = (1..3).map {
                                    PickOption("w$it", "sounds/w$it-a.mp3|sounds/w$it-b.mp3",
                                               it == 1, null)
                                }),
                        ))))
                } else MockResponse().setResponseCode(404)
            }
        }
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
    }

    @After
    fun tearDown() { runCatching { server.shutdown() } }

    private fun buttons(a: StudyActivity): List<MaterialButton> {
        val out = mutableListOf<MaterialButton>()
        fun walk(v: View) {
            if (v is MaterialButton) out.add(v)
            if (v is LinearLayout) (0 until v.childCount).forEach { walk(v.getChildAt(it)) }
        }
        walk(a.findViewById<LinearLayout>(R.id.buttonRow))
        return out
    }

    @Test
    fun `после нажатия Все прежняя отметка прослушанного снимается`() {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        val deadline = System.currentTimeMillis() + 15_000
        while (System.currentTimeMillis() < deadline &&
               buttons(a).none { it.text.contains("Выбрать") }) {
            org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle()
            Thread.sleep(10)
        }

        val listen = buttons(a).filter { it.text.contains("🔊") }
        assertEquals(3, listen.size)

        listen[0].performClick()
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle()
        a.markPlayingForTest(null)   // звук доиграл — остаётся только «прослушан»
        assertEquals("после одиночного нажатия вариант не отмечен как прослушанный",
                     "🔊 1", listen[0].text.toString())

        buttons(a).first { it.text.contains("Все") }.performClick()
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle()
        a.markPlayingForTest(1)      // пошёл второй вариант

        val marks = listen.map { it.text.toString() }
        assertEquals("во время «Все» подсвечен не ровно один вариант: $marks",
                     1, marks.count { it.contains("🔈") })
        assertTrue("осталась подкраска от прошлого одиночного нажатия: $marks",
                   marks.none { it == "🔊 1" || it == "🔊 2" || it == "🔊 3" })
    }
}
