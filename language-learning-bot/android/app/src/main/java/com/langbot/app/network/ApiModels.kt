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
    val batch_exhausted: Boolean = false,
    val loaded: Boolean = false,
    val session_stale: Boolean = false,
)

data class Card(
    val show_answer: Boolean,
    val restart_notice: String? = null,
    val content: List<CardItem>,
    val buttons: List<CardButton>,
    val meta: CardMeta,
    val sounds: List<String> = emptyList(),
    val extra_content: List<ExtraContentItem> = emptyList(),
    val big_word: BigWord? = null,
)

data class CardItem(
    val type: String,    // foreign, translation, transcription, label, notice, hint
    val text: String,
    val variant: String? = null,
    val align: String? = null,
)

data class ExtraContentItem(
    val type: String,    // label, extra
    val text: String,
    val group: String? = null,
)

data class BigWord(
    val word: String,
    val transcription: String,
)

data class CardButton(
    val id: String,      // know, show_answer, rate, toggle_skip, reconsider
    val text: String,
    val style: String,
    val rating: String? = null,
)

data class CardMeta(
    val word_id: String = "",
    val word_number: Int?,
    val session_pos: Int,
    val session_total: Int?,
    val correct_count: Int,
    val incorrect_count: Int,
    val result_history: List<String> = emptyList(),
    val pending_result: String?,
    val score_badge: ScoreBadge?,
    val hint_enabled_types: List<String> = emptyList(),
    val words_studied: Int = 0,
    val total_words: Int = 0,
    val words_for_today: Int = 0,
    val show_session_counter: Boolean = false,
    val session_counter_text: String = "",
    val is_new_word: Boolean = false,
    val new_word_label: String = "",
)

data class ScoreBadge(
    val text: String,
    val variant: String,
    val next_date: String?,
    val new_interval: Int? = null,
    val new_next_date: String? = null,
    val new_variant: String? = null,
)

data class Statistics(
    val words_studied: Int = 0,
    val words_known: Int = 0,
    val words_skipped: Int = 0,
    val words_unknown: Int = 0,
    val total_words: Int = 0,
    val words_for_today: Int = 0,
    val progress_percentage: Double = 0.0,
)

// ── Hints ─────────────────────────────────────────────────────────────────────

data class HintUpdateRequest(
    val hint_type: String,
    val text: String,
    val language_id: String? = null,
)

data class HintUpdateResponse(val ok: Boolean)

// ── Settings ──────────────────────────────────────────────────────────────────

typealias SettingsMap = Map<String, Any>

data class HelpResponse(val text: String)

data class CreateMobileTokenResponse(val code: String, val ttl_seconds: Int = 600)

data class VersionResponse(val version: String, val version_code: Int)

data class ChartManifestSection(
    val header: String,
    val charts: List<String>,
    val type: String,
)

data class ChartManifestResponse(
    val sections: List<ChartManifestSection>,
    val captions: Map<String, String>,
)
