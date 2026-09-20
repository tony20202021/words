package com.langbot.app

import com.langbot.app.network.Card
import com.langbot.app.network.CardMeta
import com.langbot.app.network.BundleWord
import com.langbot.app.offline.BundleRefresh
import com.langbot.app.offline.StoredBundle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Когда офлайн-партию качать заново.
 *
 * Прежде она перекачивалась при каждом открытии экрана занятия. Пока размер
 * был жёстко сто слов, это стоило около полутора мегабайт; теперь размер
 * выбирает человек, и на пятистах словах каждый вход стоил бы почти восемь.
 *
 * Свежее от перекачки партия всё равно не становится: устаревает она от
 * ответов, которые человек даёт ПОСЛЕ скачивания. Поэтому качаем заново, когда
 * партия кончается, когда изменили размер — и не чаще раза в полчаса в
 * остальных случаях.
 */
class BundleRefreshTest {

    private val now = 1_800_000_000_000L

    private fun card() = Card(
        show_answer = false, content = emptyList(), buttons = emptyList(),
        meta = CardMeta(word_number = 1, session_pos = 1, session_total = 1,
            correct_count = 0, incorrect_count = 0, pending_result = null,
            score_badge = null, words_for_today = 1),
    )

    private fun bundle(size: Int, cursor: Int = 0, requested: Int? = null,
                       savedAt: Long? = now) = StoredBundle(
        userId = "u1", languageId = "l1",
        words = (1..size).map {
            BundleWord(word_id = "w$it", word_number = it, card_front = card(), card_answer = card())
        },
        cursor = cursor,
        requestedSize = requested ?: size,
        savedAt = savedAt,
    )

    @Test
    fun a_missing_bundle_is_downloaded() {
        assertTrue(BundleRefresh.needed(null, 100, now))
        assertTrue(BundleRefresh.needed(bundle(0), 100, now))
    }

    @Test
    fun a_fresh_bundle_of_the_right_size_is_left_alone() {
        assertFalse(BundleRefresh.needed(bundle(100), 100, now + 60_000))
    }

    @Test
    fun changing_the_size_setting_takes_effect_at_once() {
        assertTrue("партия на сто, а просили пятьсот",
            BundleRefresh.needed(bundle(100), 500, now))
        assertTrue("партия на пятьсот, а просили пятьдесят",
            BundleRefresh.needed(bundle(500), 50, now))
    }

    @Test
    fun a_short_dictionary_does_not_cause_endless_downloads() {
        // Просили сто, а в словаре нашлось тридцать — это не повод качать снова.
        assertFalse(BundleRefresh.needed(bundle(30, requested = 100), 100, now + 60_000))
    }

    @Test
    fun a_bundle_almost_worked_through_is_replaced() {
        assertFalse("пройдена половина — рано", BundleRefresh.needed(bundle(100, cursor = 50), 100, now))
        assertTrue("пройдено три четверти — пора", BundleRefresh.needed(bundle(100, cursor = 80), 100, now))
        assertTrue("пройдена вся", BundleRefresh.needed(bundle(100, cursor = 100), 100, now))
    }

    @Test
    fun an_old_bundle_is_refreshed_but_not_more_often_than_every_half_hour() {
        assertFalse(BundleRefresh.needed(bundle(100), 100, now + BundleRefresh.MAX_AGE_MS - 1))
        assertTrue(BundleRefresh.needed(bundle(100), 100, now + BundleRefresh.MAX_AGE_MS))
    }

    @Test
    fun a_bundle_from_an_older_version_is_replaced() {
        // В партиях, сохранённых до этой версии, времени скачивания нет.
        assertTrue(BundleRefresh.needed(bundle(100, savedAt = null), 100, now))
    }

    @Test
    fun clock_moved_backwards_does_not_freeze_the_bundle() {
        assertTrue(BundleRefresh.needed(bundle(100), 100, now - 5_000))
    }

    @Test
    fun the_size_is_read_from_the_settings_the_server_sent() {
        assertEquals(250, StudyActivity.bundleSizeOf(mapOf("offline_bundle_size" to 250.0)))
        assertEquals(250, StudyActivity.bundleSizeOf(mapOf("offline_bundle_size" to "250")))
        assertEquals(StudyActivity.DEFAULT_BUNDLE_SIZE, StudyActivity.bundleSizeOf(emptyMap()))
        assertEquals(StudyActivity.DEFAULT_BUNDLE_SIZE, StudyActivity.bundleSizeOf(null))
        assertEquals(StudyActivity.DEFAULT_BUNDLE_SIZE,
            StudyActivity.bundleSizeOf(mapOf("offline_bundle_size" to "много")))
    }
}
