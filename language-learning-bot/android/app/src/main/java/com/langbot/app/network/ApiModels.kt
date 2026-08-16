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
    val pick_options: PickOptions? = null,
    val last_wrong_distractor_id: String? = null,
)

data class PickOptions(
    val target_modality: String,
    val options: List<PickOption>,
)

data class PickOption(
    val word_id: String,
    val target_text: String,
    val is_correct: Boolean,
    val offline_rating: String? = null,   // know | dont_know — server-declared for offline
)

data class CardItem(
    val type: String,    // foreign, translation, transcription, label, notice, hint
    val text: String,
    val variant: String? = null,
    val align: String? = null,
)

data class ExtraRow(
    val marker: String = "",
    val foreign: String = "",
    val ru: String = "",
)

data class ExtraContentItem(
    val type: String,    // label, extra
    val text: String,
    val group: String? = null,
    // Разобранные строки блока. Приходят с сервера, потому что формат один на
    // три клиента и разбирать его в каждом значило бы держать три копии знания.
    // Могут отсутствовать: офлайн-партии, скачанные до этой версии, хранят
    // только text — на них работает старая отрисовка одним TextView.
    val header: String? = null,
    // Заголовок тоже двуязычный, поэтому разрезан на те же две колонки.
    val header_foreign: String? = null,
    val header_ru: String? = null,
    val rows: List<ExtraRow>? = null,
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
    // Server-declared offline semantics (source of truth; see BLS card_builder):
    val offline_effect: String? = null,   // reveal_answer | reveal_question | submit
    val offline_rating: String? = null,   // rating to record when effect == submit
    // Для id="ban_pair": какой именно вариант запрещать. Правило «когда
    // показывать» живёт в card_builder, клиент только рисует пришедшее.
    val bad_word_id: String? = null,
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

// ── Offline bundle + batch results ─────────────────────────────────────────────

data class BundleWord(
    val word_id: String,
    val word_number: Int?,
    val card_front: Card,
    val card_answer: Card,
    val sounds: List<String> = emptyList(),
)

data class BundleResponse(
    // Every field needs a default: Kotlin only emits a no-arg constructor when all
    // parameters have one, and without it Gson allocates via Unsafe and skips the
    // defaults entirely — leaving `words` null despite its non-null type, which then
    // NPEs inside the prefetch and gets swallowed by runCatching.
    val session_id: String = "",
    val words: List<BundleWord> = emptyList(),
    val settings: Map<String, Any> = emptyMap(),
    val language_name_ru: String = "",
    val total_words: Int = 0,
    val words_for_today: Int = 0,
)

data class ResultEvent(
    val event_id: String,
    val word_id: String,
    val rating: String,   // know | dont_know | skip
    val ts: String,
)

data class ResultsBatchRequest(
    val user_id: String,
    val language_id: String,
    val events: List<ResultEvent>,
)

data class ResultAck(val event_id: String, val status: String)
data class ResultsBatchResponse(val acks: List<ResultAck> = emptyList())
