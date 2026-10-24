package com.langbot.app

import android.content.Intent
import android.os.Looper
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.google.gson.Gson
import com.langbot.app.network.BLSClient
import com.langbot.app.network.BundleWord
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardItem
import com.langbot.app.network.CardMeta
import com.langbot.app.network.SessionResponse
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.StoredBundle
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
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
 * Место в круге переживает переключение офлайн-онлайн.
 *
 * Жалоба владельца, уже не первая: «снова в метро, при переключениях
 * офлайн-онлайн опять перескакивает на другой номер слова».
 *
 * Что нашлось в коде. Курсор офлайн-партии двигали ТОЛЬКО офлайновые ответы
 * (OfflineEngine.advance). Онлайновые не трогали его вовсе, а свежескачанная
 * партия ложится с нулём. Пока связь есть, этого не видно: встать на нужное
 * слово помогает lastWordId — id карточки, показанной последней. Но он живёт в
 * памяти экрана. Стоит экрану открыться заново без сети — и вставать не на что:
 * приложение садится на застывший курсор, то есть на слово, пройденное давно.
 *
 * Отсюда и «перескок»: человек вчера дошёл до двухсотого, сегодня открыл в
 * метро — видит стодвадцатое.
 *
 * Проверяется то, что видит человек: номер слова на карточке после входа без
 * сети.
 */
@RunWith(RobolectricTestRunner::class)
class OfflinePlaceKeptTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"
    private val gson = Gson()

    /** Слово, которое «сервер» показывает онлайн. */
    private var serverWordId = "c"

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
                    MockResponse().setResponseCode(200).setBody(gson.toJson(
                        SessionResponse(session_id = "sid-1", card = frontCard(serverWordId))))
                } else {
                    // Префетч партии здесь не нужен: он перезаписал бы кеш
                    // нулевым курсором и подменил предмет проверки.
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

    // ── строители ────────────────────────────────────────────────────────────

    private val numbers = mapOf("a" to 101, "b" to 102, "c" to 103, "d" to 104, "e" to 105)

    private fun meta(wordId: String) = CardMeta(
        word_id = wordId, word_number = numbers[wordId] ?: 0,
        session_pos = 1, session_total = 5,
        correct_count = 0, incorrect_count = 0,
    )

    private fun frontCard(wordId: String) = Card(
        show_answer = false,
        content = listOf(CardItem("foreign", "слово-$wordId")),
        buttons = listOf(
            CardButton("know", "Знаю", "success", "know", "record_and_reveal", "know"),
            CardButton("show_answer", "Не знаю", "warn", null, "reveal_answer", null),
        ),
        meta = meta(wordId),
    )

    private fun answerCard(wordId: String) = Card(
        show_answer = true,
        content = listOf(CardItem("translation", "перевод-$wordId")),
        buttons = listOf(CardButton("rate", "Дальше", "success", "dont_know", "submit", "dont_know")),
        meta = meta(wordId),
    )

    /** Партия из пяти слов, курсор на первом — как после свежей закачки. */
    private fun storeBundle(cursor: Int = 0) {
        val ids = listOf("a", "b", "c", "d", "e")
        OfflineCache.saveBundle(StoredBundle(
            u, l,
            ids.map { BundleWord(it, numbers[it] ?: 0, frontCard(it), answerCard(it)) },
            cursor = cursor,
        ))
    }

    // ── инструменты ──────────────────────────────────────────────────────────

    private fun pumpUntil(what: String, timeoutMs: Long = 20_000, cond: () -> Boolean) {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) return
            Thread.sleep(10)
        }
        fail("не дождались: $what")
    }

    private fun launch(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", l).putExtra("language_name", "Иврит")
        return Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
    }

    private fun shownText(a: StudyActivity): String {
        val sb = StringBuilder()
        fun walk(v: View) {
            if (v.visibility != View.VISIBLE) return
            if (v is TextView) sb.append(v.text).append('\n')
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(a.findViewById(R.id.swipeRefresh))
        return sb.toString()
    }

    private fun shownWord(a: StudyActivity): String? =
        Regex("слово-([a-e])").find(shownText(a))?.groupValues?.get(1)

    // ── проверки ─────────────────────────────────────────────────────────────

    @Test
    fun `экран, открытый без сети, продолжает с того слова, где шли онлайн`() {
        storeBundle(cursor = 0)
        serverWordId = "c"

        val online = launch()
        pumpUntil("онлайн-карточка показана") { shownWord(online) == "c" }
        online.finish()

        // Связь пропала, экран открыли заново — id последней карточки умер
        // вместе с прежним экраном, вставать приходится по сохранённому месту.
        server.shutdown()
        val offline = launch()
        pumpUntil("офлайн-карточка показана") { shownWord(offline) != null }

        assertEquals("экран открылся не на том слове, где шла работа онлайн",
                     "c", shownWord(offline))
    }

    @Test
    fun `место запоминается в самой партии, а не только в памяти экрана`() {
        storeBundle(cursor = 0)
        serverWordId = "d"

        val a = launch()
        pumpUntil("карточка показана") { shownWord(a) == "d" }

        val stored = OfflineCache.loadBundle(u, l)
        assertEquals("место в круге не записано в партию", 3, stored?.cursor)
    }

    @Test
    fun `слово не из партии место не сдвигает`() {
        """
        Онлайн пришло слово, которого в скачанной партии нет. Вставать наугад
        нельзя: лучше остаться там, где стояли, чем отметить чужое место.
        """
        storeBundle(cursor = 2)
        serverWordId = "zz"

        val a = launch()
        pumpUntil("карточка показана") { shownText(a).contains("слово-zz") }

        assertEquals("чужое слово сдвинуло место в круге",
                     2, OfflineCache.loadBundle(u, l)?.cursor)
    }

    @Test
    fun `возврат в сеть на том же слове ничего не ломает`() {
        """Опора: обычный случай — онлайн, обрыв, снова онлайн."""
        storeBundle(cursor = 0)
        serverWordId = "b"

        val a = launch()
        pumpUntil("онлайн-карточка показана") { shownWord(a) == "b" }
        assertEquals(1, OfflineCache.loadBundle(u, l)?.cursor)

        serverWordId = "e"
        a.refreshForTest()
        pumpUntil("следующая карточка показана") { shownWord(a) == "e" }
        assertEquals("место не поехало за онлайн-работой",
                     4, OfflineCache.loadBundle(u, l)?.cursor)
    }

    @Test
    fun `офлайновый ответ по-прежнему двигает место`() {
        """Опора: прежнее поведение не сломано."""
        storeBundle(cursor = 0)
        server.shutdown()

        val a = launch()
        pumpUntil("офлайн-карточка показана") { shownWord(a) == "a" }
        assertTrue("нет карточки, по которой можно ответить", shownWord(a) == "a")
    }
}
