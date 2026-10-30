package com.langbot.app

import android.content.Intent
import android.os.Looper
import android.widget.LinearLayout
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.langbot.app.network.BLSClient
import com.langbot.app.network.BundleWord
import com.langbot.app.network.Card
import com.langbot.app.network.CardButton
import com.langbot.app.network.CardItem
import com.langbot.app.network.CardMeta
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.StoredBundle
import com.langbot.app.prefs.UserPrefs
import okhttp3.mockwebserver.MockWebServer
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
 * «Ой, все-таки не знаю» без сети.
 *
 * Офлайн после «Знаю» показывалась ответная сторона, отрисованная ДО ответа —
 * там этой кнопки нет. Отменить засчитанное знакомым было нечем: слово уходило
 * выученным, а интервал повторения растягивался вдвое. Онлайн кнопка есть, и
 * человек справедливо ждёт её и без сети.
 *
 * Теперь в партии три карточки: вопрос, ответ и ответ ПОСЛЕ «Знаю». Отмена без
 * сети — это более поздний ответ в очереди: сервер применяет ответы по времени,
 * и последний перекрывает прежний.
 */
@RunWith(RobolectricTestRunner::class)
class OfflineReconsiderTest {

    private lateinit var server: MockWebServer
    private val u = "user-1"
    private val l = "lang-1"

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        File(ctx.filesDir, "sounds").deleteRecursively()
        UserPrefs.saveUserId(ctx, u)
        // Сервер поднимаем и тут же гасим: сеть недоступна с первой секунды,
        // приложение уходит в офлайн на сохранённой партии.
        server = MockWebServer()
        server.start()
        BLSClient.init(server.url("/").toString().trimEnd('/'))
        server.shutdown()
    }

    @After
    fun tearDown() {
        runCatching { server.shutdown() }
    }

    private fun meta(pos: Int) = CardMeta(
        show_session_counter = true,
        session_counter_text = "(в сессии: $pos из 3)",
        word_id = "w1", word_number = pos, session_pos = pos, session_total = 3,
        correct_count = 0, incorrect_count = 0, pending_result = null, score_badge = null,
    )

    private fun front() = Card(
        show_answer = false,
        content = listOf(CardItem("foreign", "слово")),
        buttons = listOf(
            CardButton("know", "✅ Знаю", "success", "know", "record_and_reveal", "know"),
            CardButton("show_answer", "❓ Не знаю", "warn", null, "reveal_answer", null),
        ),
        meta = meta(1),
    )

    private fun answer() = Card(
        show_answer = true,
        content = listOf(CardItem("translation", "перевод")),
        buttons = listOf(CardButton("rate", "➡️ Дальше", "success", "dont_know", "submit", "dont_know")),
        meta = meta(1),
    )

    /** Ответная сторона после «Знаю» — та, что теперь приходит в партии. */
    private fun known() = Card(
        show_answer = true,
        content = listOf(CardItem("translation", "перевод")),
        buttons = listOf(
            CardButton("rate", "✅ К следующему слову", "success", "know", "advance", null),
            CardButton("reconsider", "❌ Ой, все-таки не знаю", "outline-danger",
                       null, "reveal_question", "dont_know"),
        ),
        meta = meta(1),
    )

    private fun saveBundle(withKnownCard: Boolean) {
        OfflineCache.saveBundle(
            StoredBundle(u, l, listOf(
                BundleWord("w1", 1, front(), answer(), if (withKnownCard) known() else null),
                BundleWord("w2", 2, front(), answer(), if (withKnownCard) known() else null),
            ), cursor = 0, savedAt = System.currentTimeMillis(), requestedSize = 2)
        )
    }

    private fun launch(): StudyActivity {
        val intent = Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
            .putExtra("language_id", l)
            .putExtra("language_name", "Иврит")
        val a = Robolectric.buildActivity(StudyActivity::class.java, intent).setup().get()
        pumpUntil("карточка показана офлайн") { buttonTexts(a).isNotEmpty() }
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

    private fun buttonRow(a: StudyActivity) = a.findViewById<LinearLayout>(R.id.buttonRow)

    private fun buttonTexts(a: StudyActivity): List<String> =
        (0 until buttonRow(a).childCount)
            .mapNotNull { buttonRow(a).getChildAt(it) as? MaterialButton }
            .map { it.text.toString() }

    private fun click(a: StudyActivity, contains: String) {
        val row = buttonRow(a)
        val btn = (0 until row.childCount)
            .mapNotNull { row.getChildAt(it) as? MaterialButton }
            .firstOrNull { it.text.contains(contains) }
        if (btn == null) fail("кнопки «$contains» нет, есть: ${buttonTexts(a)}") else btn.performClick()
        shadowOf(Looper.getMainLooper()).idle()
    }

    private fun outbox() = OfflineCache.loadOutbox().filter { it.userId == u && it.languageId == l }

    private fun headerText(a: StudyActivity): String {
        val sb = StringBuilder()
        fun walk(v: android.view.View) {
            if (v is android.widget.TextView) sb.append(v.text).append('\n')
            if (v is android.view.ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(a.findViewById<android.view.ViewGroup>(R.id.cardContent))
        return sb.toString()
    }

    @Test
    fun the_offline_banner_goes_away_once_the_network_is_back() {
        """
        Жалоба владельца: «включил сеть, прошёл ещё несколько слов — плашка
        офлайн не пропала». Сама она и не пропадала: выход из офлайна был
        только при загрузке сессии. Теперь после каждого ответа накопленное
        тихо пробуют отправить, и удача означает, что связь есть.
        """
        saveBundle(withKnownCard = true)
        val a = launch()
        assertTrue("плашки офлайна нет", offlineBannerShown(a))

        // Сеть вернулась: сервер принимает пачку ответов и отдаёт карточку.
        val back = MockWebServer()
        back.dispatcher = object : okhttp3.mockwebserver.Dispatcher() {
            override fun dispatch(request: okhttp3.mockwebserver.RecordedRequest):
                okhttp3.mockwebserver.MockResponse {
                val path = request.path ?: ""
                return when {
                    path.contains("results/batch") -> {
                        // Подтверждаем ровно те события, что пришли: иначе
                        // очередь не опустеет и «связь есть» не сработает.
                        val body = request.body.readUtf8()
                        val ids = Regex("\"event_id\":\"([^\"]+)\"").findAll(body)
                            .map { it.groupValues[1] }.toList()
                        val acks = ids.joinToString(",") {
                            """{"event_id":"$it","status":"ok"}"""
                        }
                        okhttp3.mockwebserver.MockResponse().setBody("""{"acks":[$acks]}""")
                    }
                    path.startsWith("/session/") -> okhttp3.mockwebserver.MockResponse()
                        .setBody(com.google.gson.Gson().toJson(
                            com.langbot.app.network.SessionResponse("sid-2", front())))
                    else -> okhttp3.mockwebserver.MockResponse().setResponseCode(404)
                }
            }
        }
        back.start()
        BLSClient.init(back.url("/").toString().trimEnd('/'))

        click(a, "Знаю")
        // Отправка идёт фоном: ждём, пока очередь опустеет, — это и есть
        // признак, что связь вернулась.
        Screenshots.pumpUntil("накопленное ушло на сервер") { outbox().isEmpty() }
        click(a, "К следующему слову")
        Screenshots.pumpUntil("экран вернулся в онлайн") { !offlineBannerShown(a) }
        assertTrue("плашка офлайна осталась после возвращения связи", !offlineBannerShown(a))
        runCatching { back.shutdown() }
    }

    private fun offlineBannerShown(a: StudyActivity): Boolean =
        // Видимостью теперь управляет коробка: текст внутри неё видим всегда.
        a.findViewById<android.view.View>(R.id.staleNotice).visibility == android.view.View.VISIBLE &&
            a.findViewById<android.widget.TextView>(R.id.tvStaleSession).text.contains("Офлайн")

    @Test
    fun the_counter_moves_offline_and_never_passes_the_round_size() {
        """
        Жалоба владельца: «в офлайн-режиме счётчик не увеличивается, показывает
        124/121». Строку «в сессии: N из M» присылает сервер, и в скачанной
        партии она застывала: позиция оттуда, размер круга отсюда.
        """
        saveBundle(withKnownCard = true)
        val a = launch()
        assertTrue("счётчик не с первого слова: ${headerText(a)}",
            headerText(a).contains("1 из 2"))

        click(a, "Знаю")
        click(a, "К следующему слову")
        val text = headerText(a)
        assertTrue("счётчик не сдвинулся: $text", text.contains("2 из 2") || text.contains("завершающее"))
        assertFalse("позиция обогнала размер круга: $text", text.contains("3 из 2"))
    }

    @Test
    fun after_know_the_answer_screen_offers_to_take_it_back() {
        saveBundle(withKnownCard = true)
        val a = launch()
        click(a, "Знаю")

        assertTrue("после «Знаю» офлайн нет кнопки отмены, есть: ${buttonTexts(a)}",
            buttonTexts(a).any { it.contains("все-таки не знаю") })
    }

    @Test
    fun taking_it_back_records_a_later_dont_know() {
        saveBundle(withKnownCard = true)
        val a = launch()
        click(a, "Знаю")
        assertEquals(listOf("know"), outbox().map { it.rating })

        click(a, "все-таки не знаю")

        val ratings = outbox().map { it.rating }
        assertEquals("поправка не записана: $ratings", listOf("know", "dont_know"), ratings)
        // Сервер применяет ответы по времени — поправка обязана быть последней.
        val entries = outbox().sortedBy { it.ts }
        assertEquals("dont_know", entries.last().rating)
        assertEquals("поправка должна быть о том же слове", "w1", entries.last().word_id)
    }

    @Test
    fun taking_it_back_moves_on_just_like_online() {
        """
        Жалоба владельца: «нажимаю "ой все-таки не знаю" — ожидаю что перейду
        на следующее слово, так в онлайн режиме. Но в офлайн возвращается снова
        на слово, которое проходил, и надо отвечать "не знаю" ещё раз».

        Онлайн /reconsider ставит «не знаю» И листает дальше — одним действием.
        Офлайн возвращал на вопрос того же слова: поправка записана, а круг
        стоит, и человек отвечает второй раз за то же слово.
        """
        saveBundle(withKnownCard = true)
        val a = launch()
        click(a, "Знаю")
        click(a, "все-таки не знаю")

        // Позицию смотрим по сохранённому месту в круге: на последнем слове
        // заголовок пишется иначе («завершающее»), и по тексту не отличить.
        assertEquals("круг не сдвинулся после поправки, заголовок: ${headerText(a)}",
                     1, OfflineCache.loadBundle(u, l)?.cursor)
        val texts = buttonTexts(a)
        assertTrue("показан не вопрос следующего слова, а кнопки: $texts",
            texts.any { it.contains("Знаю") } && texts.none { it.contains("все-таки") })
    }

    @Test
    fun taking_it_back_does_not_answer_the_next_word_for_you() {
        """
        Переход не должен тащить поправку на следующее слово: в очереди ровно
        два ответа, и оба — о первом.
        """
        saveBundle(withKnownCard = true)
        val a = launch()
        click(a, "Знаю")
        click(a, "все-таки не знаю")

        val entries = outbox().sortedBy { it.ts }
        assertEquals("лишние записи в очереди: ${entries.map { it.word_id to it.rating }}",
                     2, entries.size)
        assertTrue("поправка ушла не за то слово: ${entries.map { it.word_id }}",
                   entries.all { it.word_id == "w1" })
    }

    @Test
    fun without_a_rating_from_the_server_we_stay_on_the_word() {
        """
        Старый сервер мог прислать кнопку без оценки — действие тогда
        подставляется по её id. Листать в этом случае нельзя: поправку никто не
        записал, и переход потерял бы её молча. Остаётся прежнее поведение.
        """
        OfflineCache.saveBundle(
            StoredBundle(u, l, listOf(
                BundleWord("w1", 1, front(), answer(), Card(
                    show_answer = true,
                    content = listOf(CardItem("translation", "перевод")),
                    buttons = listOf(
                        CardButton("rate", "✅ К следующему слову", "success", "know", "advance", null),
                        // без offline_rating — как у старого сервера
                        CardButton("reconsider", "❌ Ой, все-таки не знаю", "outline-danger",
                                   null, "reveal_question", null),
                    ),
                    meta = meta(1),
                )),
                BundleWord("w2", 2, front(), answer(), known()),
            ), cursor = 0, savedAt = System.currentTimeMillis(), requestedSize = 2)
        )
        val a = launch()
        click(a, "Знаю")
        click(a, "все-таки не знаю")

        assertEquals("круг сдвинулся, хотя поправку никто не записал",
                     0, OfflineCache.loadBundle(u, l)?.cursor)
        assertEquals(listOf("know"), outbox().map { it.rating })
    }

    @Test
    fun moving_on_after_know_does_not_record_the_word_twice() {
        saveBundle(withKnownCard = true)
        val a = launch()
        click(a, "Знаю")
        click(a, "К следующему слову")

        assertEquals("слово записано дважды: ${outbox().map { it.rating }}", 1, outbox().size)
    }

    @Test
    fun a_bundle_from_an_older_version_still_works() {
        // В партиях, скачанных до этой версии, третьей карточки нет: показываем
        // обычную ответную — как и раньше, без кнопки отмены, но без поломки.
        saveBundle(withKnownCard = false)
        val a = launch()
        click(a, "Знаю")

        assertTrue("ответ не показан: ${buttonTexts(a)}",
            buttonTexts(a).any { it.contains("Дальше") })
        assertEquals(listOf("know"), outbox().map { it.rating })
    }
}
