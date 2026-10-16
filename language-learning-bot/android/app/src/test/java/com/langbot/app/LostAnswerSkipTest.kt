package com.langbot.app

import android.content.Intent
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.test.core.app.ApplicationProvider
import com.google.android.material.button.MaterialButton
import com.langbot.app.network.BLSClient
import com.langbot.app.offline.OfflineCache
import com.langbot.app.prefs.UserPrefs
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.android.controller.ActivityController

/**
 * Ни одно слово круга не должно пропасть при переключениях связи.
 *
 * Жалоба владельца: «повторить ошибку не удалось, но она точно была — в метро,
 * при переключениях офлайн-онлайн такое ощущение, что перескакивает на слово
 * вперёд».
 *
 * Разбор кода даёт подозреваемого: обрыв ПОСЛЕ того, как сервер уже обработал
 * запрос. Телефон ответа не получил, считает, что не вышло, уходит в офлайн и
 * записывает оценку ещё раз — а сервер тем временем уже сдвинул сессию.
 * Вернувшись в онлайн, человек попадает на слово ПОСЛЕ того, которого не видел.
 *
 * Обычные проверки это не ловили: там связь рвётся ДО обработки, и сервер
 * остаётся на месте. Поэтому у поддельного сервера появился отдельный режим —
 * сделать работу и потерять ответ.
 *
 * Проверяется не «как должно выглядеть», а свойство: показанные слова идут
 * подряд, без дыр. Пропуск — это когда после слова N следующим показали N+2,
 * ни разу не показав N+1.
 */
@RunWith(RobolectricTestRunner::class)
class LostAnswerSkipTest {

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
        waitForCard()
    }

    private fun root(): View? = study?.get()?.findViewById(R.id.swipeRefresh)

    private fun texts(root: View?): String {
        if (root == null) return ""
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

    private fun waitForCard() {
        runCatching {
            Screenshots.pumpUntil("экран ответил", timeoutMs = 25_000) {
                buttons().isNotEmpty() || texts(root()).contains("пройдена")
            }
        }
    }

    /** Номер слова на карточке, как его видит человек. */
    private fun shownWord(): Int? =
        Regex("Слово номер: (\\d+)").find(texts(root()))?.groupValues?.get(1)?.toIntOrNull()

    private fun tap(contains: String): Boolean {
        val btn = buttons().firstOrNull { it.text.contains(contains) } ?: return false
        val before = buttons().map { it.text.toString() } to texts(root())
        btn.performClick()
        runCatching {
            Screenshots.pumpUntil("экран ответил на «$contains»", timeoutMs = 25_000) {
                (buttons().map { it.text.toString() } to texts(root())) != before
            }
        }
        return true
    }

    private fun answerAndAdvance(seen: MutableList<Int>) {
        shownWord()?.let { if (seen.lastOrNull() != it) seen.add(it) }
        if (!tap("Знаю")) return
        shownWord()?.let { if (seen.lastOrNull() != it) seen.add(it) }
        if (!tap("К следующему слову")) tap("Дальше")
        shownWord()?.let { if (seen.lastOrNull() != it) seen.add(it) }
    }

    private fun assertNoGaps(seen: List<Int>) {
        val order = seen.distinct()
        val gaps = order.zipWithNext().filter { (a, b) -> b > a + 1 }
        assertTrue("круг перескочил через слово: показаны $order, разрывы $gaps",
                   gaps.isEmpty())
    }

    @Test
    fun `потерянный ответ не уносит следующее слово`() {
        val seen = mutableListOf<Int>()
        open()
        answerAndAdvance(seen)

        // Сервер работу делает, ответ теряется — телефон уходит в офлайн.
        bls.dropResponses = true
        answerAndAdvance(seen)
        // Сторож самой проверки: если телефон не ушёл в офлайн, значит потеря
        // ответа до него не дошла, и дальше проверять нечего — она бы прошла
        // на чём угодно.
        assertTrue("телефон не заметил потерю ответа — сценарий не воспроизведён",
                   texts(root()).contains("Офлайн") || OfflineCache.pendingCount() > 0)

        // Связь вернулась: накопленное уходит, сессия догоняет.
        bls.dropResponses = false
        bls.online = true
        answerAndAdvance(seen)
        answerAndAdvance(seen)

        assertNoGaps(seen)
    }

    @Test
    fun `несколько потерянных ответов подряд не рвут круг`() {
        val seen = mutableListOf<Int>()
        open()
        answerAndAdvance(seen)

        bls.dropResponses = true
        repeat(3) { answerAndAdvance(seen) }

        bls.dropResponses = false
        repeat(2) { answerAndAdvance(seen) }

        assertNoGaps(seen)
    }

    @Test
    fun `обрыв ДО обработки слово не теряет`() {
        """Опора: обычный обрыв — тот, что проверки ловили и раньше."""
        val seen = mutableListOf<Int>()
        open()
        answerAndAdvance(seen)

        bls.online = false
        answerAndAdvance(seen)
        bls.online = true
        answerAndAdvance(seen)
        answerAndAdvance(seen)

        assertNoGaps(seen)
    }

    @Test
    fun `сервер и телефон сходятся в числе отвеченных слов`() {
        """
        Второе свойство того же: сколько слов человек прошёл, столько сервер и
        должен знать. Перескок через слово оставил бы его неотвеченным.
        """
        val seen = mutableListOf<Int>()
        open()
        answerAndAdvance(seen)
        bls.dropResponses = true
        answerAndAdvance(seen)
        bls.dropResponses = false
        answerAndAdvance(seen)

        Screenshots.pumpUntil("накопленное ушло на сервер", timeoutMs = 25_000) {
            OfflineCache.pendingCount() == 0
        }
        val answered = bls.answered.keys.map { it.removePrefix("w").toInt() }.sorted()
        assertEquals("у сервера отвечены не те слова, что видел человек",
                     seen.distinct().take(answered.size), answered)
    }
}
