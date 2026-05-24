package com.langbot.app.network

import com.google.gson.annotations.SerializedName

data class MobileActivateRequest(val code: String)
data class MobileActivateResponse(val user_id: String)

data class Language(
    val id: String,
    val name_ru: String,
    val name_foreign: String,
)

data class StartSessionRequest(
    val user_id: String,
    val language_id: String,
)

data class RateRequest(val rating: String)

data class SessionResponse(
    val session_id: String?,
    val card: Card?,
    val no_words: Boolean = false,
)

data class Card(
    val show_answer: Boolean,
    val content: List<CardItem>,
    val buttons: List<CardButton>,
    val meta: CardMeta,
    val sounds: List<String> = emptyList(),
)

data class CardItem(
    val type: String,    // foreign, translation, transcription, label, notice, hint
    val text: String,
    val variant: String? = null,
    val align: String? = null,
)

data class CardButton(
    val id: String,      // know, show_answer, rate, toggle_skip, reconsider
    val text: String,
    val style: String,
    val rating: String? = null,
)

data class CardMeta(
    val word_number: Int?,
    val session_pos: Int,
    val session_total: Int?,
    val correct_count: Int,
    val incorrect_count: Int,
    val result_history: List<String> = emptyList(),
    val pending_result: String?,
    val score_badge: ScoreBadge?,
)

data class ScoreBadge(
    val text: String,
    val variant: String,
    val next_date: String?,
)

data class Statistics(
    val words_studied: Int = 0,
    val words_known: Int = 0,
    val words_skipped: Int = 0,
    val total_words: Int = 0,
    val words_for_today: Int = 0,
    val progress_percentage: Double = 0.0,
)
