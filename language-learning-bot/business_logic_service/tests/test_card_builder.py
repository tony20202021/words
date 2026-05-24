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
    def test_interval_notice_after_know(self):
        session = make_session(score_changed=True)
        word = make_word(score=1, interval=7)
        card = build_card(session, word, show_answer=True)
        notices = [i for i in card["content"] if i["type"] == "notice" and i["variant"] == "success"]
        assert any("7" in n["text"] for n in notices)

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
