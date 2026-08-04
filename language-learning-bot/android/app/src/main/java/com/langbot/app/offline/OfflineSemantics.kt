package com.langbot.app.offline

/**
 * Compatibility fallback for interpreting card buttons offline.
 *
 * The source of truth for offline action semantics is the SERVER: `build_card`
 * stamps every button with `offline_effect` / `offline_rating`. This object is
 * used ONLY when those server fields are absent — e.g. an older cached bundle
 * produced before the app/BLS were upgraded. It intentionally mirrors the BLS
 * button ids so a stale bundle still behaves; fresh bundles never hit it.
 *
 * Pure functions — no Android deps — so they can be unit-tested on the JVM.
 */
object OfflineSemantics {

    /** One of: "reveal_answer" | "reveal_question" | "submit"; null = ignore offline. */
    fun effectFor(btnId: String): String? = when (btnId) {
        "show_answer" -> "reveal_answer"
        "reconsider"  -> "reveal_question"
        "know", "rate", "toggle_skip" -> "submit"
        else -> null
    }

    /** Rating to record when the effect is "submit". */
    fun ratingFor(btnId: String, rating: String?): String = when (btnId) {
        "know" -> "know"
        "toggle_skip" -> "skip"
        "rate" -> rating ?: "dont_know"
        else -> "dont_know"
    }
}
