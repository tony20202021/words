package com.langbot.app.offline

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Pure-JVM unit tests for the offline layer's business-rule-free helpers.
 * No Android framework, no emulator — run with `./gradlew testReleaseUnitTest`.
 */
class OfflineLogicTest {

    // ── AudioCache.fileNameFor ──────────────────────────────────────────────

    @Test
    fun fileNameFor_sanitizes_path_separators_and_strips_leading_slash() {
        assertEquals("he_1_2_3.mp3", AudioCache.fileNameFor("/he/1/2/3.mp3"))
        assertEquals("he_1_2_3.mp3", AudioCache.fileNameFor("he/1/2/3.mp3"))
    }

    @Test
    fun fileNameFor_keeps_safe_chars_and_replaces_unsafe() {
        assertEquals("a-b_c.d", AudioCache.fileNameFor("a-b c.d"))
        assertEquals("x_y_z.mp3", AudioCache.fileNameFor("x:y?z.mp3"))
    }

    @Test
    fun fileNameFor_is_deterministic() {
        val p = "voice/he-IL/word_42.mp3"
        assertEquals(AudioCache.fileNameFor(p), AudioCache.fileNameFor(p))
    }

    // ── OfflineSemantics (compat fallback for stale bundles) ────────────────

    @Test
    fun effectFor_maps_known_button_ids() {
        assertEquals("reveal_answer", OfflineSemantics.effectFor("show_answer"))
        assertEquals("reveal_question", OfflineSemantics.effectFor("reconsider"))
        assertEquals("submit", OfflineSemantics.effectFor("know"))
        assertEquals("submit", OfflineSemantics.effectFor("rate"))
        assertEquals("submit", OfflineSemantics.effectFor("toggle_skip"))
    }

    @Test
    fun effectFor_returns_null_for_unknown_button() {
        assertNull(OfflineSemantics.effectFor("add_forbidden_pair"))
        assertNull(OfflineSemantics.effectFor(""))
    }

    @Test
    fun ratingFor_maps_button_ids_to_ratings() {
        assertEquals("know", OfflineSemantics.ratingFor("know", null))
        assertEquals("skip", OfflineSemantics.ratingFor("toggle_skip", null))
        assertEquals("know", OfflineSemantics.ratingFor("rate", "know"))
        assertEquals("dont_know", OfflineSemantics.ratingFor("rate", "dont_know"))
        assertEquals("dont_know", OfflineSemantics.ratingFor("rate", null))
    }

    // ── OfflineCache.tsOf (chronological == lexicographic) ──────────────────

    @Test
    fun tsOf_is_zero_padded_to_20_chars() {
        assertEquals(20, OfflineCache.tsOf(1L).length)
        assertEquals("00000000000000000001", OfflineCache.tsOf(1L))
    }

    @Test
    fun tsOf_preserves_chronological_order_lexicographically() {
        val earlier = OfflineCache.tsOf(1_000L)
        val later = OfflineCache.tsOf(2_000_000_000_000L)
        assertTrue(earlier < later)
    }
}
