package com.langbot.app

import androidx.test.core.app.ApplicationProvider
import com.langbot.app.network.BundleWord
import com.langbot.app.network.Card
import com.langbot.app.network.CardMeta
import com.langbot.app.offline.OfflineCache
import com.langbot.app.offline.StoredBundle
import com.langbot.app.offline.StudyDay
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.time.Instant

/**
 * Учебные сутки на телефоне — те же, что у сервера.
 *
 * Было: офлайн-счётчик считал день по местной полуночи устройства, а сервер —
 * по своей границе. При начале суток в 4 утра занятие в полпервого ночи без
 * сети обнуляло счётчик пройденного, хотя для сервера это ещё вчерашний день.
 * Границ суток в системе было четыре; теперь одна, и телефон знает её из
 * настроек, приехавших в офлайн-партии.
 */
@RunWith(RobolectricTestRunner::class)
class StudyDayTest {

    private val u = "user-1"
    private val l = "lang-1"

    private fun at(iso: String): Long = Instant.parse(iso).toEpochMilli()

    @Before
    fun setUp() {
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        OfflineCache.init(ctx)
        ctx.filesDir.listFiles()?.forEach { if (it.isFile) it.delete() }
    }

    private fun bundleWith(settings: Map<String, Any>?) {
        OfflineCache.saveBundle(StoredBundle(
            userId = u, languageId = l,
            words = listOf(BundleWord(
                word_id = "w1", word_number = 1,
                card_front = Card(meta = CardMeta(word_id = "w1")),
                card_answer = Card(meta = CardMeta(word_id = "w1")),
            )),
            settings = settings,
        ))
    }

    @Test
    fun `ночь до начала суток относится ко вчерашнему дню`() {
        // 01:30 по Риму = 23:30 UTC предыдущего дня; сутки начинаются в 4.
        assertEquals("2026-10-09", StudyDay.of(at("2026-10-09T23:30:00Z"), "Europe/Rome", 4))
        assertEquals("2026-10-09", StudyDay.of(at("2026-10-10T01:59:00Z"), "Europe/Rome", 4))
        assertEquals("2026-10-10", StudyDay.of(at("2026-10-10T02:01:00Z"), "Europe/Rome", 4))
    }

    @Test
    fun `перевод часов не сдвигает начало суток по местному времени`() {
        // В Риме 25.10.2026 переходят с +02:00 на +01:00. 04:00 по-местному
        // остаётся 04:00: летом это 02:00 UTC, зимой 03:00.
        assertEquals("2026-10-20", StudyDay.of(at("2026-10-20T02:01:00Z"), "Europe/Rome", 4))
        assertEquals("2026-10-29", StudyDay.of(at("2026-10-30T02:01:00Z"), "Europe/Rome", 4))
        assertEquals("2026-10-30", StudyDay.of(at("2026-10-30T03:01:00Z"), "Europe/Rome", 4))
    }

    @Test
    fun `без настроек граница остаётся полночью UTC`() {
        assertEquals("2026-10-09", StudyDay.of(at("2026-10-09T23:59:00Z"), "UTC", 0))
        assertEquals("2026-10-10", StudyDay.of(at("2026-10-10T00:01:00Z"), "UTC", 0))
    }

    @Test
    fun `опечатка в названии пояса не роняет занятие`() {
        assertEquals("2026-10-09", StudyDay.of(at("2026-10-09T23:30:00Z"), "Нет/Такого", 0))
    }

    @Test
    fun `правило берётся из партии, а не из часов устройства`() {
        bundleWith(mapOf("timezone" to "Europe/Rome", "day_start_hour" to 4.0))
        // 00:30 по Риму — по часам устройства уже новый день, по правилу ещё нет.
        assertEquals("2026-10-09", OfflineCache.studyToday(u, l, at("2026-10-09T22:30:00Z")))
        assertEquals("2026-10-10", OfflineCache.studyToday(u, l, at("2026-10-10T02:30:00Z")))
    }

    @Test
    fun `партия без настроек даёт прежнее поведение`() {
        bundleWith(null)
        assertEquals("2026-10-10", OfflineCache.studyToday(u, l, at("2026-10-10T00:30:00Z")))
    }

    @Test
    fun `счётчик пройденного переживает местную полночь`() {
        """
        Главная причина правки. Начало суток в 4 утра: в полпервого ночи без
        сети отсчёт обязан остаться вчерашним, а не обнулиться.
        """
        bundleWith(mapOf("timezone" to "Europe/Rome", "day_start_hour" to 4.0))
        OfflineCache.saveProgress(u, l, correct = 3, wrong = 1, history = listOf("know"))
        val kept = OfflineCache.loadProgress(u, l)
        assertNotNull("отсчёт пропал сразу после сохранения", kept)
        assertEquals(3, kept!!.correct)
        assertEquals("2026-10-09",
            StudyDay.of(at("2026-10-09T22:30:00Z"), "Europe/Rome", 4))
    }

    @Test
    fun `новая партия пересматривает правило`() {
        """
        Человек поменял пояс — партия перекачалась, и правило обязано стать
        новым, а не остаться в памяти от прошлой.
        """
        bundleWith(mapOf("timezone" to "UTC", "day_start_hour" to 0.0))
        assertEquals("2026-10-10", OfflineCache.studyToday(u, l, at("2026-10-10T00:30:00Z")))
        bundleWith(mapOf("timezone" to "Europe/Rome", "day_start_hour" to 4.0))
        assertEquals("2026-10-09", OfflineCache.studyToday(u, l, at("2026-10-10T00:30:00Z")))
    }

    @Test
    fun `отсчёт прошлых суток не возвращается`() {
        """Старый день — старые числа; показывать их как сегодняшние нельзя."""
        bundleWith(mapOf("timezone" to "UTC", "day_start_hour" to 0.0))
        OfflineCache.saveProgress(u, l, correct = 5, wrong = 2, history = emptyList())
        // Подменяем день в сохранённом отсчёте на вчерашний.
        val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()
        val f = java.io.File(ctx.filesDir, "progress_${u}_${l}.json")
        f.writeText(f.readText().replace(
            Regex("\"day\":\"[^\"]*\""), "\"day\":\"1999-01-01\""))
        assertNull("вернулся отсчёт прошлых суток", OfflineCache.loadProgress(u, l))
    }
}
