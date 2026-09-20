package com.langbot.app

import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BundleWord
import com.langbot.app.network.Card
import com.langbot.app.network.CardMeta
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.OfflineEngine
import com.langbot.app.offline.StoredBundle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * Перезапуск сессии офлайн.
 *
 * Онлайн «начать заново» отдаёт только оставшиеся на сегодня слова — сервер
 * пересчитывает набор и уже отвеченное не выдаёт. Офлайн партия скачана
 * целиком, и без вывода отвеченного круг начинался с тех же слов, а счётчик
 * «N из M» показывал прежнее M, хотя слов осталось меньше.
 */
@RunWith(RobolectricTestRunner::class)
class OfflineRestartTest {

    private val u = "u1"
    private val l = "l1"

    private fun card() = Card(
        show_answer = false, content = emptyList(), buttons = emptyList(),
        meta = CardMeta(word_number = 1, session_pos = 1, session_total = 3,
            correct_count = 0, incorrect_count = 0, pending_result = null,
            score_badge = null, words_for_today = 3),
    )

    private fun bundle(vararg ids: String) = StoredBundle(
        userId = u, languageId = l,
        words = ids.map { BundleWord(word_id = it, word_number = 1, card_front = card(), card_answer = card()) },
    )

    @Before
    fun setUp() {
        OfflineCache.init(ApplicationProvider.getApplicationContext())
        OfflineCache.removeEvents(OfflineCache.loadOutbox().map { it.event_id }.toSet())
        OfflineCache.saveBundle(bundle("w1", "w2", "w3"))
    }

    @Test
    fun a_fresh_bundle_holds_every_word() {
        val eng = OfflineEngine.fromStore(u, l)!!
        assertEquals(3, eng.total)
        assertEquals("w1", eng.currentWordId())
    }

    @Test
    fun restart_drops_the_words_the_person_knows() {
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.excludeAnswered(u, l)

        val eng = OfflineEngine.fromStore(u, l)!!
        // Круг короче на известные, и начинается с первого оставшегося.
        assertEquals(2, eng.total)
        assertEquals("w2", eng.currentWordId())
        assertTrue(eng.isExcluded("w1"))
        assertFalse(eng.isExcluded("w2"))
    }

    @Test
    fun a_word_answered_dont_know_comes_round_again() {
        // Правило сервера: «не знаю» стирает дату проверки, и слово остаётся в
        // обороте. Офлайн выводил его из круга наравне с известными — и в
        // самолёте пройденная партия объявлялась законченной, хотя половину
        // слов человек как раз не знает.
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.addResult(u, l, "w2", "dont_know")
        OfflineCache.addResult(u, l, "w3", "skip")
        OfflineCache.excludeAnswered(u, l)

        val eng = OfflineEngine.fromStore(u, l)!!
        assertEquals(1, eng.total)
        assertEquals("w2", eng.currentWordId())
        assertFalse("«не знаю» обязано остаться в круге", eng.isExcluded("w2"))
        assertTrue(eng.isExcluded("w1"))
        assertTrue("пропущенное выводится, как и известное", eng.isExcluded("w3"))
    }

    @Test
    fun answers_stay_in_the_outbox_for_syncing() {
        OfflineCache.addResult(u, l, "w1", "know")
        OfflineCache.excludeAnswered(u, l)
        // Выведены из круга — но не потеряны: их всё ещё надо отправить серверу.
        assertEquals(1, OfflineCache.loadOutbox().count { it.userId == u })
    }

    @Test
    fun a_bundle_saved_before_this_version_keeps_all_its_words() {
        // В старых партиях поля excluded нет, и Gson кладёт туда null вопреки
        // типу: круг не должен от этого опустеть.
        OfflineCache.saveBundle(bundle("w1", "w2").copy(excluded = null))
        val eng = OfflineEngine.fromStore(u, l)!!
        assertEquals(2, eng.total)
    }
}
