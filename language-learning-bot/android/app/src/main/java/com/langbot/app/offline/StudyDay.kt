package com.langbot.app.offline

import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset

/**
 * Учебные сутки на телефоне — та же граница, что у сервера.
 *
 * Зачем свой кусок. Без сети спросить сервер не у кого, а сутки за ночь в
 * самолёте успевают смениться. Правило простое и повторяет серверное
 * (common/study_day.py): берём время в поясе человека и отступаем назад на
 * час начала суток — всё, что раньше него, относится ко вчерашнему дню.
 *
 * Пояс хранится названием, а не смещением: «Europe/Rome» переживает перевод
 * часов сам, числом пришлось бы править дважды в год.
 */
object StudyDay {

    /** Дата учебных суток в виде «2026-10-09». */
    fun of(nowMillis: Long, timezone: String, dayStartHour: Int): String {
        val zone = runCatching { ZoneId.of(timezone) }.getOrDefault(ZoneOffset.UTC)
        return Instant.ofEpochMilli(nowMillis)
            .atZone(zone)
            .minusHours(dayStartHour.coerceIn(0, 23).toLong())
            .toLocalDate()
            .toString()
    }
}
