package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.langbot.app.network.BLSClient
import com.langbot.app.network.NetworkRetry
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.android.controller.ActivityController

/**
 * Попытки соединения не останавливают занятие.
 *
 * Владелец, 04.11.2026: связь пропала, висела плашка соединения, он не
 * дождался и нажал ответ — и всё прошло дальше. «Если это осознанная
 * реализация, получилось хорошо: попытки коннекта не останавливают процесс.
 * Надо оставить это сознательно».
 *
 * Осознанной она не была. Блокировки кнопок в экране нет вовсе: setLoading
 * только показывает полоску, флага «запрос в полёте» не существует, каждое
 * нажатие запускает свою корутину. Работало это потому, что от двойной записи
 * прикрывают две защиты, поставленные совсем для другого: word_processed на
 * сервере и offlineCurrentRecorded в офлайн-движке.
 *
 * Поведение решено оставить. Значит его надо закрепить: случайность, на
 * которую никто не смотрит, однажды исчезает вместе с рефакторингом одной из
 * этих двух защит. Здесь проверяется не устройство, а обещание, которое
 * плашка теперь даёт человеку вслух.
 */
@RunWith(RobolectricTestRunner::class)
class AnswerWhileConnectingTest {

    private lateinit var bls: FakeBls
    private var study: ActivityController<StudyActivity>? = null

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
        UserPrefs.saveUserId(ctx, "user-1")
        bls = FakeBls(words = (1..8).toList())
        bls.start()
        BLSClient.init(bls.url())
    }

    @After
    fun tearDown() {
        study?.let { runCatching { it.pause().stop().destroy() } }
        bls.shutdown()
    }

    private fun open() {
        study = Robolectric.buildActivity(
            StudyActivity::class.java,
            Intent(ApplicationProvider.getApplicationContext(), StudyActivity::class.java)
                .putExtra("language_id", "lang-1").putExtra("language_name", "Иврит"),
        ).setup()
        runCatching {
            Screenshots.pumpUntil("экран ответил", timeoutMs = 25_000) {
                buttons().isNotEmpty() || texts().contains("пройдена")
            }
        }
    }

    private fun texts(): String {
        val root: View = study?.get()?.findViewById(R.id.swipeRefresh) ?: return ""
        val sb = StringBuilder()
        fun walk(v: View) {
            if (v.visibility != View.VISIBLE) return
            if (v is TextView) sb.append(v.text).append('\n')
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(root)
        return sb.toString()
    }

    private fun buttons(): List<MaterialButton> {
        val out = mutableListOf<MaterialButton>()
        fun walk(v: View?) {
            if (v is MaterialButton) out.add(v)
            if (v is ViewGroup) for (i in 0 until v.childCount) walk(v.getChildAt(i))
        }
        walk(study?.get()?.findViewById(R.id.buttonRow))
        return out
    }

    private fun shownWord(): Int? =
        Regex("Слово номер: (\\d+)").find(texts())?.groupValues?.get(1)?.toIntOrNull()

    private fun correctCount(): Int =
        Regex("(\\d+) правильны").find(texts())?.groupValues?.get(1)?.toIntOrNull() ?: 0

    private fun tap(contains: String): Boolean {
        val btn = buttons().firstOrNull { it.text.contains(contains) } ?: return false
        val before = buttons().map { it.text.toString() } to texts()
        btn.performClick()
        runCatching {
            Screenshots.pumpUntil("экран ответил на «$contains»", timeoutMs = 25_000) {
                (buttons().map { it.text.toString() } to texts()) != before
            }
        }
        return true
    }

    private fun status(attempt: Int) =
        NetworkRetry.Status(attempt = attempt, total = 3, timeoutMs = 6000, lastError = null)

    // ── плашка говорит, что ждать не обязательно ────────────────────────────

    @Test
    fun the_notice_invites_answering_instead_of_waiting() {
        open()
        val a = study!!.get()

        for (attempt in 1..3) {
            val text = a.connectionNoticeText(status(attempt))
            assertTrue(
                "плашка попытки $attempt не разрешает отвечать: «$text»",
                text.contains(StudyActivity.ANSWER_WHILE_CONNECTING))
        }
    }

    @Test
    fun the_notice_still_says_what_is_happening() {
        /* Опора: разрешение не должно вытеснить саму причину плашки. */
        open()
        val a = study!!.get()

        assertTrue(a.connectionNoticeText(status(1)).contains("Соединяемся"))
        assertTrue(a.connectionNoticeText(status(2)).contains("Попытка 2 из 3"))
    }

    // ── нажатие во время обрыва ─────────────────────────────────────────────

    @Test
    fun an_answer_pressed_with_no_network_is_not_swallowed() {
        open()
        val first = shownWord()
        bls.online = false

        assertTrue("кнопки ответа пропали", tap("Знаю"))
        tap("К следующему слову")

        assertTrue("после ответа без сети экран остался на том же слове: $first",
            shownWord() != first || texts().contains("Офлайн"))
    }

    @Test
    fun a_word_answered_once_is_counted_once_even_with_the_network_gone() {
        /*
         * Главная опора. Нажатие во время попытки соединения не блокируется, и
         * ничто не мешает человеку нажать ещё раз. Оценка при этом обязана
         * записаться ровно одна: на сервере за это отвечает word_processed, в
         * офлайне — offlineCurrentRecorded. Проверка держит обе.
         */
        open()
        // Пакет для офлайна обязан приехать ДО обрыва. Без него приложение не
        // уходит в офлайн, а показывает «нет сети и нет сохранённой сессии»,
        // и ответ не записывается вовсе. Успел он или нет — вопрос времени,
        // поэтому прежде проверка молча меряла то одно, то другое: по
        // отдельности зелёная, в общем прогоне падала.
        runCatching {
            Screenshots.pumpUntil("офлайн-пакет сохранён", timeoutMs = 25_000) {
                OfflineCache.loadBundle("user-1", "lang-1") != null
            }
        }
        assertTrue("офлайн-пакет не приехал — проверять нечего",
            OfflineCache.loadBundle("user-1", "lang-1") != null)
        bls.online = false

        val btn = buttons().firstOrNull { it.text.contains("Знаю") }
        assertTrue("кнопки «Знаю» нет", btn != null)
        // Ждать надо смены состояния, а не появления слова «правильных»: оно
        // есть на экране с самого начала, со значением 0. Прежнее условие
        // выполнялось мгновенно, проверка читала счётчик до обработки ответа
        // и держалась на везении — 07.11.2026 везение кончилось.
        val было = buttons().map { it.text.toString() } to texts()
        btn!!.performClick()
        btn.performClick()          // второе нажатие, пока первое ещё в пути
        runCatching {
            Screenshots.pumpUntil("экран ответил на двойное нажатие", timeoutMs = 25_000) {
                (buttons().map { it.text.toString() } to texts()) != было
            }
        }

        assertEquals("ответ засчитан не один раз: " +
            "${texts().lines().firstOrNull { it.contains("правильны") }}",
            1, correctCount())
    }

    @Test
    fun the_notice_is_gone_while_the_network_is_fine() {
        /* Опора против обратной ошибки: плашка не должна висеть всегда. */
        open()
        tap("Знаю")

        val notice = study?.get()?.findViewById<TextView>(R.id.tvConnection)
        assertFalse("плашка связи висит при живом сервере",
            notice != null && notice.visibility == View.VISIBLE)
    }
}
