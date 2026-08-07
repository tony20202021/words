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

    /**
     * One of: "reveal_answer" | "reveal_question" | "record_and_reveal" |
     * "submit" | "advance"; null = ignore offline.
     *
     * `know` records the rating and reveals the answer WITHOUT advancing — the
     * same two-step flow as online (`know_word` then `rate_word`). Treating it
     * as a plain submit skipped the answer card entirely and looked like the app
     * jumped straight to the next word.
     *
     * `rate` stays a submit here: without the server stamp we cannot tell the
     * already-scored case from the not-yet-scored one, and recording a duplicate
     * is safer than losing a result — the outbox dedups by event_id server-side.
     */
    fun effectFor(btnId: String): String? = when (btnId) {
        "show_answer" -> "reveal_answer"
        "reconsider"  -> "reveal_question"
        "know"        -> "record_and_reveal"
        "rate", "toggle_skip" -> "submit"
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
