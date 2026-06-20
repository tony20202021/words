"""Unit tests for card_builder — no I/O, no async, pure logic."""

import pytest
from app.services.card_builder import build_card, _parse_sound_urls


# ── helpers ───────────────────────────────────────────────────────────────────

def make_session(show_mode="foreign", score_changed=False, word_processed=False,
                 show_answer=False, correct=0, incorrect=0, settings=None,
                 prev_score=None, prev_interval=None, prev_next_check_date=None):
    s = {
        "session_id": "test-session",
        "user_id": "u1",
        "language_id": "lang1",
        "show_mode": show_mode,
        "score_changed": score_changed,
        "word_processed": word_processed,
        "show_answer": show_answer,
        "total_words_processed": correct + incorrect,
        "correct_count": correct,
        "incorrect_count": incorrect,
        "settings": settings or {"show_sounds": True},
    }
    if prev_score is not None:
        s["prev_score"] = prev_score
    if prev_interval is not None:
        s["prev_interval"] = prev_interval
    if prev_next_check_date is not None:
        s["prev_next_check_date"] = prev_next_check_date
    return s


def make_word(foreign="hello", translation="привет", transcription="[hɛˈloʊ]",
              score=-1, interval=0, next_check_date="", is_skipped=False, sounds=None):
    uwd = {"score": score, "check_interval": interval,
           "next_check_date": next_check_date, "is_skipped": is_skipped}
    return {
        "word_number": 1,
        "word_foreign": foreign,
        "translation": translation,
        "transcription": transcription,
        "sounds": sounds,
        "user_word_data": uwd,
    }


def content_types(card):
    return [i["type"] for i in card["content"]]


def content_texts(card):
    return [i["text"] for i in card["content"]]


def button_ids(card):
    return [b["id"] for b in card["buttons"]]


# ── before answer ─────────────────────────────────────────────────────────────

class TestBeforeAnswer:
    def test_foreign_mode_shows_foreign_word(self):
        card = build_card(make_session("foreign"), make_word(), show_answer=False)
        assert not card["show_answer"]
        assert "foreign" in content_types(card)
        assert "translation" not in content_types(card)
        assert "transcription" not in content_types(card)

    def test_translation_mode_shows_translation_only(self):
        card = build_card(make_session("translation"), make_word(), show_answer=False)
        assert "translation" in content_types(card)
        assert "foreign" not in content_types(card)
        assert "transcription" not in content_types(card)

    def test_transcription_mode_shows_transcription_only(self):
        card = build_card(make_session("transcription"), make_word(), show_answer=False)
        assert "transcription" in content_types(card)
        assert "foreign" not in content_types(card)
        assert "translation" not in content_types(card)

    def test_sound_mode_shows_label_only(self):
        card = build_card(make_session("sound"), make_word(), show_answer=False)
        assert "foreign" not in content_types(card)
        assert "translation" not in content_types(card)
        assert "transcription" not in content_types(card)
        labels = [i for i in card["content"] if i["type"] == "label"]
        assert any("звуку" in l["text"] for l in labels)

    def test_before_answer_buttons(self):
        card = build_card(make_session(), make_word(), show_answer=False)
        ids = button_ids(card)
        assert "know" in ids
        assert "show_answer" in ids
        assert "toggle_skip" in ids
        assert "rate" not in ids

    def test_sound_mode_includes_sounds(self):
        import json
        sounds_json = json.dumps({"1": "path/to/sound.mp3"})
        card = build_card(make_session("sound"), make_word(sounds=sounds_json), show_answer=False)
        assert card["sounds"] == ["path/to/sound.mp3"]

    def test_non_sound_mode_no_sounds_before_answer(self):
        import json
        sounds_json = json.dumps({"1": "path/to/sound.mp3"})
        card = build_card(make_session("foreign"), make_word(sounds=sounds_json), show_answer=False)
        assert card["sounds"] == []


# ── after answer ──────────────────────────────────────────────────────────────

class TestAfterAnswer:
    def test_shows_all_fields(self):
        card = build_card(make_session(), make_word(), show_answer=True)
        assert card["show_answer"]
        types = content_types(card)
        assert "foreign" in types
        assert "transcription" in types
        assert "translation" in types

    def test_order_translation_transcription_foreign(self):
        card = build_card(make_session(), make_word(), show_answer=True)
        types = [i["type"] for i in card["content"] if i["type"] in ("foreign", "transcription", "translation")]
        assert types == ["translation", "transcription", "foreign"]

    def test_always_shows_all_regardless_of_mode(self):
        for mode in ("foreign", "translation", "transcription", "sound"):
            card = build_card(make_session(mode), make_word(), show_answer=True)
            types = content_types(card)
            assert "foreign" in types, f"foreign missing in mode={mode}"
            assert "translation" in types, f"translation missing in mode={mode}"
            assert "transcription" in types, f"transcription missing in mode={mode}"

    def test_after_answer_buttons(self):
        card = build_card(make_session(), make_word(), show_answer=True)
        ids = button_ids(card)
        assert "rate" in ids
        assert "toggle_skip" in ids
        assert "know" not in ids
        assert "show_answer" not in ids

    def test_sounds_shown_after_answer(self):
        import json
        sounds_json = json.dumps({"1": "path/to/sound.mp3"})
        for mode in ("foreign", "translation", "transcription"):
            card = build_card(make_session(mode), make_word(sounds=sounds_json), show_answer=True)
            assert card["sounds"] == ["path/to/sound.mp3"], f"sounds missing after answer in mode={mode}"

    def test_no_transcription_when_word_has_none(self):
        word = make_word(transcription="")
        word["transcription"] = ""
        card = build_card(make_session(), word, show_answer=True)
        assert "transcription" not in content_types(card)


# ── score / interval notices ──────────────────────────────────────────────────

class TestNotices:
    def test_new_interval_in_badge_after_know(self):
        # Success notice removed — new interval now lives in score_badge.new_interval
        session = make_session(score_changed=True)
        word = make_word(score=1, interval=7, next_check_date="2026-06-02")
        card = build_card(session, word, show_answer=True)
        notices = [i for i in card["content"] if i["type"] == "notice" and i["variant"] == "success"]
        assert notices == []
        badge = card["meta"]["score_badge"]
        assert badge.get("new_interval") == 7
        assert badge.get("new_next_date") == "2026-06-02"

    def test_previous_interval_notice_when_already_known(self):
        session = make_session(score_changed=False)
        word = make_word(score=1, interval=14)
        card = build_card(session, word, show_answer=True)
        notices = [i for i in card["content"] if i["type"] == "notice" and i["variant"] == "info"]
        assert any("14" in n["text"] for n in notices)

    def test_no_interval_notice_before_answer(self):
        session = make_session(score_changed=True)
        word = make_word(score=1, interval=7)
        card = build_card(session, word, show_answer=False)
        notices = [i for i in card["content"] if i["type"] == "notice" and i["variant"] in ("success", "info")]
        assert notices == []

    def test_skip_notice_when_skipped(self):
        word = make_word(is_skipped=True)
        card = build_card(make_session(), word, show_answer=False)
        notices = [i for i in card["content"] if i["type"] == "notice" and i["variant"] == "secondary"]
        assert len(notices) == 1

    def test_no_skip_notice_when_not_skipped(self):
        card = build_card(make_session(), make_word(is_skipped=False), show_answer=False)
        notices = [i for i in card["content"] if i["type"] == "notice" and i["variant"] == "secondary"]
        assert notices == []


# ── score badge ───────────────────────────────────────────────────────────────

class TestScoreBadge:
    def test_new_word(self):
        card = build_card(make_session(), make_word(score=-1), show_answer=False)
        assert card["meta"]["score_badge"]["variant"] == "secondary"

    def test_known_word(self):
        card = build_card(make_session(), make_word(score=1, interval=3), show_answer=False)
        badge = card["meta"]["score_badge"]
        assert badge["variant"] == "success"
        assert "3" in badge["text"]

    def test_unknown_word(self):
        card = build_card(make_session(), make_word(score=0), show_answer=False)
        assert card["meta"]["score_badge"]["variant"] == "danger"

    def test_badge_shows_old_interval_after_know(self):
        # word now has interval=8 (after update), but session stores prev_interval=4
        session = make_session(score_changed=True, prev_score=1, prev_interval=4,
                               prev_next_check_date="2026-01-01")
        word = make_word(score=1, interval=8, next_check_date="2026-01-09")
        card = build_card(session, word, show_answer=True)
        badge = card["meta"]["score_badge"]
        assert "4" in badge["text"]
        assert badge["next_date"] == "2026-01-01"

    def test_badge_shows_old_state_when_was_unknown_before(self):
        # word was unknown (score=0) before show_answer; now it's score=0 after update — still danger
        session = make_session(score_changed=False, prev_score=0)
        word = make_word(score=0, interval=1)
        card = build_card(session, word, show_answer=True)
        assert card["meta"]["score_badge"]["variant"] == "danger"

    def test_badge_uses_current_values_before_answer(self):
        # before answer, prev_* should be ignored
        session = make_session(prev_score=0, prev_interval=0)
        word = make_word(score=1, interval=5)
        card = build_card(session, word, show_answer=False)
        badge = card["meta"]["score_badge"]
        assert badge["variant"] == "success"
        assert "5" in badge["text"]


# ── rate button rating value ──────────────────────────────────────────────────

class TestRateButton:
    def test_rate_know_when_score_changed(self):
        card = build_card(make_session(score_changed=True), make_word(), show_answer=True)
        rate_btn = next(b for b in card["buttons"] if b["id"] == "rate")
        assert rate_btn["rating"] == "know"

    def test_rate_dont_know_when_not_score_changed(self):
        card = build_card(make_session(score_changed=False), make_word(), show_answer=True)
        rate_btn = next(b for b in card["buttons"] if b["id"] == "rate")
        assert rate_btn["rating"] == "dont_know"


# ── skip button text ──────────────────────────────────────────────────────────

class TestSkipButton:
    def test_skip_text_when_not_skipped(self):
        card = build_card(make_session(), make_word(is_skipped=False), show_answer=False)
        skip_btn = next(b for b in card["buttons"] if b["id"] == "toggle_skip")
        assert "Пропускать" in skip_btn["text"]
        assert "Не пропускать" not in skip_btn["text"]

    def test_unskip_text_when_skipped(self):
        card = build_card(make_session(), make_word(is_skipped=True), show_answer=False)
        skip_btn = next(b for b in card["buttons"] if b["id"] == "toggle_skip")
        assert "Не пропускать" in skip_btn["text"]

    def test_skip_present_after_answer_score_changed(self):
        card = build_card(make_session(score_changed=True), make_word(), show_answer=True)
        assert "toggle_skip" in button_ids(card)

    def test_skip_present_after_answer_not_score_changed(self):
        card = build_card(make_session(score_changed=False), make_word(), show_answer=True)
        assert "toggle_skip" in button_ids(card)

    def test_reconsider_present_only_when_score_changed(self):
        card_changed = build_card(make_session(score_changed=True), make_word(), show_answer=True)
        card_unchanged = build_card(make_session(score_changed=False), make_word(), show_answer=True)
        assert "reconsider" in button_ids(card_changed)
        assert "reconsider" not in button_ids(card_unchanged)


# ── meta ──────────────────────────────────────────────────────────────────────

class TestMeta:
    def test_counters(self):
        card = build_card(make_session(correct=3, incorrect=2), make_word(), show_answer=False)
        assert card["meta"]["correct_count"] == 3
        assert card["meta"]["incorrect_count"] == 2
        assert card["meta"]["session_pos"] == 6  # total_processed + 1

    def test_sounds_disabled_in_settings(self):
        import json
        sounds_json = json.dumps({"1": "path/to/sound.mp3"})
        session = make_session("sound", settings={"show_sounds": False})
        card = build_card(session, make_word(sounds=sounds_json), show_answer=False)
        assert card["sounds"] == []


# ── session_total ─────────────────────────────────────────────────────────────

class TestSessionTotal:
    def _session_with_batch(self, words_for_today=0, batch_size=2, processed=0):
        """Session with a small batch (simulates multi-batch flow)."""
        s = make_session(correct=processed)
        s["words"] = [f"word_{i}" for i in range(batch_size)]
        s["current_index"] = 0
        if words_for_today:
            s["words_for_today"] = words_for_today
        return s

    def test_uses_words_for_today_not_batch_size(self):
        # Bug: session_total was showing batch size (2) instead of total (51)
        session = self._session_with_batch(words_for_today=51, batch_size=2)
        card = build_card(session, make_word(), show_answer=False)
        assert card["meta"]["session_total"] == 51

    def test_stable_mid_session(self):
        # After processing 6 words, session_total must still reflect the full plan
        session = self._session_with_batch(words_for_today=51, batch_size=2, processed=6)
        card = build_card(session, make_word(), show_answer=False)
        assert card["meta"]["session_total"] == 51
        assert card["meta"]["session_pos"] == 7  # processed + 1

    def test_fallback_to_batch_when_words_for_today_zero(self):
        # words_for_today not set → fall back to batch calculation
        session = self._session_with_batch(words_for_today=0, batch_size=5, processed=3)
        card = build_card(session, make_word(), show_answer=False)
        # batch calc: processed(3) + remaining(5-0=5) = 8
        assert card["meta"]["session_total"] == 8

    def test_fallback_when_words_for_today_missing(self):
        # words_for_today key absent entirely
        s = make_session(correct=2)
        s["words"] = ["a", "b", "c"]
        s["current_index"] = 1
        card = build_card(s, make_word(), show_answer=False)
        # batch calc: 2 + (3-1) = 4
        assert card["meta"]["session_total"] == 4


# ── pending_result ────────────────────────────────────────────────────────────

class TestPendingResult:
    def test_none_before_answer_shown(self):
        card = build_card(make_session(show_answer=False, score_changed=False), make_word(), show_answer=False)
        assert card["meta"]["pending_result"] is None

    def test_none_before_answer_even_when_score_changed(self):
        card = build_card(make_session(show_answer=True, score_changed=True), make_word(), show_answer=False)
        assert card["meta"]["pending_result"] is None

    def test_know_when_score_changed_after_answer(self):
        card = build_card(make_session(score_changed=True), make_word(), show_answer=True)
        assert card["meta"]["pending_result"] == "know"

    def test_dont_know_when_score_not_changed_after_answer(self):
        card = build_card(make_session(score_changed=False), make_word(), show_answer=True)
        assert card["meta"]["pending_result"] == "dont_know"


# ── _parse_sound_urls ─────────────────────────────────────────────────────────

class TestParseSoundUrls:
    def test_empty(self):
        assert _parse_sound_urls({}) == []
        assert _parse_sound_urls({"sounds": None}) == []

    def test_single_sound(self):
        import json
        word = {"sounds": json.dumps({"1": "path/a.mp3"})}
        assert _parse_sound_urls(word) == ["path/a.mp3"]

    def test_multiple_sounds_sorted(self):
        import json
        word = {"sounds": json.dumps({"2": "b.mp3", "1": "a.mp3"})}
        assert _parse_sound_urls(word) == ["a.mp3", "b.mp3"]

    def test_double_encoded(self):
        import json
        inner = json.dumps({"1": "path/x.mp3"})
        word = {"sounds": json.dumps(inner)}
        assert _parse_sound_urls(word) == ["path/x.mp3"]


# ── big_word ──────────────────────────────────────────────────────────────────

class TestBigWord:
    def test_returned_when_show_big_and_show_answer(self):
        session = make_session(settings={"show_sounds": True, "show_big": True})
        word = make_word(foreign="应当")
        card = build_card(session, word, show_answer=True)
        assert card["big_word"] is not None
        assert card["big_word"]["word"] == "应当"

    def test_includes_transcription(self):
        session = make_session(settings={"show_sounds": True, "show_big": True})
        word = make_word(foreign="应当", transcription="yīngdāng")
        card = build_card(session, word, show_answer=True)
        assert card["big_word"]["transcription"] == "yīngdāng"

    def test_none_before_answer(self):
        session = make_session(settings={"show_sounds": True, "show_big": True})
        word = make_word(foreign="应当")
        card = build_card(session, word, show_answer=False)
        assert card["big_word"] is None

    def test_none_when_show_big_false(self):
        session = make_session(settings={"show_sounds": True, "show_big": False})
        word = make_word(foreign="应当")
        card = build_card(session, word, show_answer=True)
        assert card["big_word"] is None

    def test_none_when_show_big_missing_from_settings(self):
        session = make_session(settings={"show_sounds": True})
        word = make_word(foreign="应当")
        card = build_card(session, word, show_answer=True)
        assert card["big_word"] is None

    def test_none_when_no_word_foreign(self):
        session = make_session(settings={"show_sounds": True, "show_big": True})
        word = make_word(foreign="")
        card = build_card(session, word, show_answer=True)
        assert card["big_word"] is None

    def test_empty_transcription_becomes_empty_string(self):
        session = make_session(settings={"show_sounds": True, "show_big": True})
        word = make_word(foreign="hello", transcription="")
        card = build_card(session, word, show_answer=True)
        assert card["big_word"] is not None
        assert card["big_word"]["transcription"] == ""


# ── extra_content groups ──────────────────────────────────────────────────────

class TestExtraContentGroups:
    def test_tones_items_have_group_tones(self):
        session = make_session(settings={"show_sounds": True, "show_tones": True})
        word = make_word()
        word["tones"] = "1声 2声"
        card = build_card(session, word, show_answer=True)
        groups = {i.get("group") for i in card["extra_content"]}
        assert "tones" in groups

    def test_references_items_have_group_references(self):
        session = make_session(settings={"show_sounds": True, "show_references": True})
        word = make_word()
        word["references"] = "[1] 应该"
        card = build_card(session, word, show_answer=True)
        groups = {i.get("group") for i in card["extra_content"]}
        assert "references" in groups

    def test_radicals_items_have_group_radicals(self):
        session = make_session(settings={"show_sounds": True, "show_radicals": True})
        word = make_word()
        word["radicals"] = "[1] 木"
        card = build_card(session, word, show_answer=True)
        groups = {i.get("group") for i in card["extra_content"]}
        assert "radicals" in groups

    def test_all_items_in_group_have_group_field(self):
        session = make_session(settings={"show_sounds": True, "show_tones": True, "show_references": True})
        word = make_word()
        word["tones"] = "tones data"
        word["references"] = "refs data"
        card = build_card(session, word, show_answer=True)
        for item in card["extra_content"]:
            assert "group" in item, f"item missing group: {item}"

    def test_tones_absent_when_setting_off(self):
        session = make_session(settings={"show_sounds": True, "show_tones": False})
        word = make_word()
        word["tones"] = "tones data"
        card = build_card(session, word, show_answer=True)
        groups = {i.get("group") for i in card["extra_content"]}
        assert "tones" not in groups

    def test_extra_content_empty_before_answer(self):
        session = make_session(settings={"show_sounds": True, "show_tones": True})
        word = make_word()
        word["tones"] = "tones data"
        card = build_card(session, word, show_answer=False)
        assert card["extra_content"] == []

    def test_extra_content_empty_when_word_field_blank(self):
        session = make_session(settings={"show_sounds": True, "show_tones": True})
        word = make_word()
        word["tones"] = "   "
        card = build_card(session, word, show_answer=True)
        groups = {i.get("group") for i in card["extra_content"]}
        assert "tones" not in groups


# ── meta: language + word counts ──────────────────────────────────────────────

class TestMetaLanguageFields:
    def test_language_names_passed_through(self):
        session = make_session()
        session["language_name_ru"] = "Китайский"
        session["language_name_foreign"] = "中文"
        card = build_card(session, make_word(), show_answer=False)
        assert card["meta"]["language_name_ru"] == "Китайский"
        assert card["meta"]["language_name_foreign"] == "中文"

    def test_language_names_default_empty(self):
        card = build_card(make_session(), make_word(), show_answer=False)
        assert card["meta"]["language_name_ru"] == ""
        assert card["meta"]["language_name_foreign"] == ""

    def test_words_studied_passed_through(self):
        session = make_session()
        session["words_studied"] = 42
        session["total_words"] = 100
        session["words_for_today"] = 10
        card = build_card(session, make_word(), show_answer=False)
        assert card["meta"]["words_studied"] == 42
        assert card["meta"]["total_words"] == 100
        assert card["meta"]["words_for_today"] == 10

    def test_word_counts_default_zero(self):
        card = build_card(make_session(), make_word(), show_answer=False)
        assert card["meta"]["words_studied"] == 0
        assert card["meta"]["total_words"] == 0
        assert card["meta"]["words_for_today"] == 0

    def test_result_history_passed_through(self):
        session = make_session()
        session["result_history"] = ["know", "dont_know", "know"]
        card = build_card(session, make_word(), show_answer=False)
        assert card["meta"]["result_history"] == ["know", "dont_know", "know"]


# ── hint display + settings ───────────────────────────────────────────────────

class TestHintDisplay:
    def _make_word_with_hints(self):
        w = make_word()
        w["user_word_data"]["hint_meaning"]             = "ассоциация"
        w["user_word_data"]["hint_phoneticsound"]       = "ни-хао"
        w["user_word_data"]["hint_phoneticassociation"] = "фонетика"
        w["user_word_data"]["hint_writing"]             = "написание"
        return w

    def test_hints_hidden_when_settings_off(self):
        """All hint settings False → no hint items in content."""
        session = make_session(settings={
            "show_hint_meaning": False,
            "show_hint_phoneticsound": False,
            "show_hint_phoneticassociation": False,
            "show_hint_writing": False,
        })
        card = build_card(session, self._make_word_with_hints(), show_answer=False)
        assert not any(i["type"] == "hint" for i in card["content"])

    def test_hint_meaning_shown_when_enabled(self):
        session = make_session(settings={"show_hint_meaning": True})
        card = build_card(session, self._make_word_with_hints(), show_answer=False)
        hint_texts = [i["text"] for i in card["content"] if i["type"] == "hint"]
        assert any("ассоциация" in t for t in hint_texts)

    def test_only_enabled_hint_types_appear(self):
        """Only phoneticsound enabled → only that hint in content."""
        session = make_session(settings={"show_hint_phoneticsound": True})
        card = build_card(session, self._make_word_with_hints(), show_answer=False)
        hint_texts = [i["text"] for i in card["content"] if i["type"] == "hint"]
        assert len(hint_texts) == 1
        assert "ни-хао" in hint_texts[0]

    def test_all_four_hint_types_shown_when_all_enabled(self):
        session = make_session(settings={
            "show_hint_meaning": True,
            "show_hint_phoneticsound": True,
            "show_hint_phoneticassociation": True,
            "show_hint_writing": True,
        })
        card = build_card(session, self._make_word_with_hints(), show_answer=True)
        hint_texts = [i["text"] for i in card["content"] if i["type"] == "hint"]
        assert len(hint_texts) == 4

    def test_hint_not_shown_when_value_empty(self):
        """Setting enabled but no value → no hint item."""
        w = make_word()  # no hints set in uwd
        session = make_session(settings={"show_hint_meaning": True})
        card = build_card(session, w, show_answer=False)
        assert not any(i["type"] == "hint" for i in card["content"])

    def test_hint_enabled_types_in_meta_empty_when_all_off(self):
        session = make_session(settings={})
        card = build_card(session, make_word(), show_answer=False)
        assert card["meta"]["hint_enabled_types"] == []

    def test_hint_enabled_types_in_meta_reflects_settings(self):
        session = make_session(settings={
            "show_hint_meaning": True,
            "show_hint_writing": True,
        })
        card = build_card(session, make_word(), show_answer=False)
        enabled = card["meta"]["hint_enabled_types"]
        assert "meaning" in enabled
        assert "writing" in enabled
        assert "phoneticsound" not in enabled
        assert "phoneticassociation" not in enabled

    def test_word_level_hint_shown_when_no_uwd_hint(self):
        """Word-level (admin) hint shown when user has no personal hint, if type enabled."""
        w = make_word()
        w["hint_meaning"] = "слово-подсказка"
        session = make_session(settings={"show_hint_meaning": True})
        card = build_card(session, w, show_answer=False)
        hint_texts = [i["text"] for i in card["content"] if i["type"] == "hint"]
        assert any("слово-подсказка" in t for t in hint_texts)

    def test_uwd_hint_overrides_word_hint(self):
        """User's personal hint takes precedence over admin word hint."""
        w = make_word()
        w["hint_meaning"] = "слово-подсказка"
        w["user_word_data"]["hint_meaning"] = "личная"
        session = make_session(settings={"show_hint_meaning": True})
        card = build_card(session, w, show_answer=False)
        hint_texts = [i["text"] for i in card["content"] if i["type"] == "hint"]
        assert any("личная" in t for t in hint_texts)
        assert not any("слово-подсказка" in t for t in hint_texts)


# ── Task 5: restart recommendation notice ────────────────────────────────────

class TestRestartNotice:
    def _session_at_limit(self, word_number=10, words_studied=9, incorrect=12, limit=10):
        s = make_session(incorrect=incorrect, settings={"unknown_limit_new_words": limit})
        s["words_studied"] = words_studied
        return s

    def _word_at_boundary(self, word_number=10):
        w = make_word()
        w["word_number"] = word_number
        return w

    def test_notice_shown_when_at_boundary_and_over_limit(self):
        """word_number >= words_studied AND incorrect >= limit → restart_notice set."""
        session = self._session_at_limit(word_number=10, words_studied=9, incorrect=12, limit=10)
        card = build_card(session, self._word_at_boundary(10), show_answer=False)
        assert card["restart_notice"] is not None
        assert "Рекомендуется" in card["restart_notice"]

    def test_no_notice_when_below_error_limit(self):
        session = self._session_at_limit(incorrect=5, limit=10)
        card = build_card(session, self._word_at_boundary(10), show_answer=False)
        assert card["restart_notice"] is None

    def test_no_notice_when_word_below_studied_boundary(self):
        """word_number < words_studied → still studying old words, no notice."""
        session = self._session_at_limit(words_studied=50, incorrect=15, limit=10)
        card = build_card(session, self._word_at_boundary(word_number=5), show_answer=False)
        assert card["restart_notice"] is None

    def test_notice_also_shown_after_answer(self):
        """Notice shown both before and after answer."""
        session = self._session_at_limit(words_studied=9, incorrect=12, limit=10)
        card = build_card(session, self._word_at_boundary(10), show_answer=True)
        assert card["restart_notice"] is not None
        assert "Рекомендуется" in card["restart_notice"]

    def test_no_notice_when_words_studied_zero(self):
        """words_studied=0 means fresh start, boundary check skipped."""
        s = make_session(incorrect=15, settings={"unknown_limit_new_words": 5})
        s["words_studied"] = 0
        w = make_word()
        w["word_number"] = 1
        card = build_card(s, w, show_answer=False)
        assert card["restart_notice"] is None

    def test_notice_text_contains_counts(self):
        session = self._session_at_limit(incorrect=15, limit=10)
        card = build_card(session, self._word_at_boundary(10), show_answer=False)
        assert "15" in card["restart_notice"]
        assert "10" in card["restart_notice"]

    def test_notice_not_in_content_list(self):
        """restart_notice must not pollute content[] — it has its own top-level field."""
        session = self._session_at_limit(incorrect=12, limit=10)
        card = build_card(session, self._word_at_boundary(10), show_answer=False)
        warnings_in_content = [c for c in card["content"] if c.get("variant") == "warning"]
        assert warnings_in_content == []


# ── References filtering ──────────────────────────────────────────────────────

class TestReferencesFiltering:
    def _word_with_refs(self, refs: str):
        w = make_word()
        w["references"] = refs
        return w

    def test_refs_shown_unfiltered_when_words_studied_zero(self):
        """words_studied=0 → no filtering, all refs shown."""
        refs = "[#5]word5\n[#100]word100"
        session = make_session(settings={"show_references": True})
        card = build_card(session, self._word_with_refs(refs), show_answer=True)
        extra_texts = [i["text"] for i in card["extra_content"] if i["type"] == "extra"]
        assert any("word100" in t for t in extra_texts)

    def test_refs_filtered_by_words_studied(self):
        """Lines with [#N] > words_studied are hidden."""
        refs = "[#5]word5\n[#100]word100\n[#20]word20"
        session = make_session(settings={"show_references": True})
        session["words_studied"] = 25
        card = build_card(session, self._word_with_refs(refs), show_answer=True)
        extra_texts = [i["text"] for i in card["extra_content"] if i["type"] == "extra"]
        combined = "\n".join(extra_texts)
        assert "word5" in combined
        assert "word20" in combined
        assert "word100" not in combined

    def test_refs_fully_filtered_leave_no_extra_block(self):
        """All ref lines filtered out → no 'references' block in extra_content."""
        refs = "[#999]word999"
        session = make_session(settings={"show_references": True})
        session["words_studied"] = 10
        card = build_card(session, self._word_with_refs(refs), show_answer=True)
        assert not any(i.get("group") == "references" for i in card["extra_content"])

    def test_refs_line_without_number_always_shown(self):
        """Lines without [#N] marker are never filtered."""
        refs = "generic reference line\n[#500]numbered"
        session = make_session(settings={"show_references": True})
        session["words_studied"] = 10
        card = build_card(session, self._word_with_refs(refs), show_answer=True)
        extra_texts = [i["text"] for i in card["extra_content"] if i["type"] == "extra"]
        combined = "\n".join(extra_texts)
        assert "generic reference line" in combined
        assert "numbered" not in combined


class TestSessionCounterMeta:
    def test_new_word_flag(self):
        session = make_session()
        session["words_studied"] = 10
        w = make_word()
        w["word_number"] = 15
        card = build_card(session, w, show_answer=False)
        assert card["meta"]["is_new_word"] is True
        assert card["meta"]["show_session_counter"] is False
        assert "первый раз" in card["meta"]["new_word_label"]

    def test_session_counter_for_review_word(self):
        session = make_session()
        session["words_studied"] = 50
        session["words_for_today"] = 10
        w = make_word()
        w["word_number"] = 5
        card = build_card(session, w, show_answer=False)
        assert card["meta"]["is_new_word"] is False
        assert card["meta"]["show_session_counter"] is True
        assert "в сессии" in card["meta"]["session_counter_text"]
