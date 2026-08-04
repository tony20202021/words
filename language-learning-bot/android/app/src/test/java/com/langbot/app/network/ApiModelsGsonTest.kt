package com.langbot.app.network

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Pure-JVM checks that JSON coming from BLS lands in the data classes without loss.
 *
 * These guard the Android side of the "BLS is the single source of truth" contract:
 * the server stamps offline_effect / offline_rating and the client must read them
 * rather than re-deriving the rules. A silent rename on either side would make the
 * offline engine fall back to nulls, so it is worth pinning down.
 */
class ApiModelsGsonTest {

    private val gson = Gson()

    @Test
    fun card_button_carries_server_stamped_offline_semantics() {
        val json = """
            {"id":"know","text":"Знаю","style":"success",
             "rating":"know","offline_effect":"submit","offline_rating":"know"}
        """.trimIndent()

        val b = gson.fromJson(json, CardButton::class.java)
        assertEquals("know", b.id)
        assertEquals("submit", b.offline_effect)
        assertEquals("know", b.offline_rating)
    }

    @Test
    fun card_button_without_offline_fields_parses_with_nulls() {
        val b = gson.fromJson("""{"id":"show_answer","text":"Не знаю","style":"warn"}""", CardButton::class.java)
        assertEquals("show_answer", b.id)
        assertNull(b.offline_effect)
        assertNull(b.offline_rating)
    }

    @Test
    fun pick_option_carries_offline_rating() {
        val json = """
            {"target_modality":"translation",
             "options":[{"word_id":"w1","target_text":"дом","is_correct":true,"offline_rating":"know"},
                        {"word_id":"w2","target_text":"стол","is_correct":false,"offline_rating":"dont_know"}]}
        """.trimIndent()

        val p = gson.fromJson(json, PickOptions::class.java)
        assertEquals(2, p.options.size)
        assertEquals("know", p.options[0].offline_rating)
        assertEquals("dont_know", p.options[1].offline_rating)
        assertTrue(p.options[0].is_correct)
    }

    @Test
    fun bundle_response_parses_words_with_both_card_sides_and_sounds() {
        val json = """
            {"session_id":"s1",
             "words":[{"word_id":"w1","word_number":15,
                       "card_front":{"show_answer":false,"content":[],"buttons":[],
                                     "meta":{"word_number":15,"session_pos":1,"session_total":3,
                                             "correct_count":0,"incorrect_count":0,
                                             "pending_result":null,"score_badge":null}},
                       "card_answer":{"show_answer":true,"content":[],"buttons":[],
                                      "meta":{"word_number":15,"session_pos":1,"session_total":3,
                                              "correct_count":0,"incorrect_count":0,
                                              "pending_result":null,"score_badge":null}},
                       "sounds":["sounds/he/gtts/15.mp3","sounds/he/hila/15.mp3"]}]}
        """.trimIndent()

        val r = gson.fromJson(json, BundleResponse::class.java)
        assertEquals("s1", r.session_id)
        assertEquals(1, r.words.size)
        val w = r.words[0]
        assertEquals("w1", w.word_id)
        assertEquals(15, w.word_number)
        assertEquals(false, w.card_front.show_answer)
        assertEquals(true, w.card_answer.show_answer)
        assertEquals(2, w.sounds.size)
        assertEquals(1, w.card_front.meta.session_pos)
    }

    @Test
    fun bundle_response_defaults_words_to_empty_when_absent() {
        val r = gson.fromJson("""{"session_id":"s1"}""", BundleResponse::class.java)
        assertNotNull(r.words)
        assertTrue(r.words.isEmpty())
    }

    @Test
    fun results_batch_request_serializes_the_field_names_the_server_expects() {
        val req = ResultsBatchRequest(
            user_id = "u1",
            language_id = "l1",
            events = listOf(ResultEvent(event_id = "e1", word_id = "w1", rating = "know", ts = "00000000000000000001")),
        )
        val json = gson.toJson(req)

        // BLS reads these exact keys — see business_logic_service/app/routers/results.py.
        assertTrue(json, json.contains("\"user_id\""))
        assertTrue(json, json.contains("\"language_id\""))
        assertTrue(json, json.contains("\"event_id\""))
        assertTrue(json, json.contains("\"word_id\""))
        assertTrue(json, json.contains("\"rating\""))
        assertTrue(json, json.contains("\"ts\""))
    }

    @Test
    fun results_batch_response_parses_acks() {
        val r = gson.fromJson(
            """{"acks":[{"event_id":"e1","status":"ok"},{"event_id":"e2","status":"duplicate"}]}""",
            ResultsBatchResponse::class.java,
        )
        assertEquals(2, r.acks.size)
        assertEquals("ok", r.acks[0].status)
        assertEquals("duplicate", r.acks[1].status)
    }

    @Test
    fun results_batch_response_defaults_to_empty_acks() {
        val r = gson.fromJson("{}", ResultsBatchResponse::class.java)
        assertNotNull(r.acks)
        assertTrue(r.acks.isEmpty())
    }
}
