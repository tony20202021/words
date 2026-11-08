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
        assert "rate" not in ids
        # «Пропускать» переехала на экран ответа: исключать слово решают, увидев
        # его целиком, а на вопросной стороне нет ни перевода, ни произношения.
        assert "toggle_skip" not in ids

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

    def test_previous_interval_lives_in_the_badge_not_in_a_notice(self):
        """
        Большую плашку «Вы знали это слово» убрали: компактный бейдж в шапке
        говорит то же самое («знал · N дн.»), а два сообщения об одном и том же
        на одном экране лишние.
        """
        session = make_session(score_changed=False)
        word = make_word(score=1, interval=14)
        card = build_card(session, word, show_answer=True)

        notices = [i for i in card["content"] if i["type"] == "notice" and i["variant"] == "info"]
        assert notices == [], notices
        assert "14" in str(card["meta"]["score_badge"]), card["meta"]["score_badge"]

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
        card = build_card(make_session(), make_word(is_skipped=False), show_answer=True)
        skip_btn = next(b for b in card["buttons"] if b["id"] == "toggle_skip")
        assert "Пропускать" in skip_btn["text"]
        assert "Не пропускать" not in skip_btn["text"]

    def test_unskip_text_when_skipped(self):
        card = build_card(make_session(), make_word(is_skipped=True), show_answer=True)
        skip_btn = next(b for b in card["buttons"] if b["id"] == "toggle_skip")
        assert "Не пропускать" in skip_btn["text"]

    def test_skip_absent_before_answer(self):
        card = build_card(make_session(), make_word(), show_answer=False)
        assert "toggle_skip" not in button_ids(card)

    def test_skip_obeys_the_setting_on_the_answer_side(self):
        """
        Кнопка показывается только при включённой галке show_skip_button.
        Проверки на ВЫКЛЮЧЕННУЮ настройку не было ни одной, а именно этот случай
        и ломался молча: в пик-режиме настройка не работала вовсе, и заметить
        это было нечем — карточка выглядела правдоподобно в обоих положениях.
        """
        word = make_word()
        for score_changed in (True, False):
            on = build_card(make_session(show_answer=True, score_changed=score_changed,
                                         settings={"show_skip_button": True}),
                            word, show_answer=True)
            off = build_card(make_session(show_answer=True, score_changed=score_changed,
                                          settings={"show_skip_button": False}),
                             word, show_answer=True)
            assert "toggle_skip" in button_ids(on), score_changed
            assert "toggle_skip" not in button_ids(off), score_changed
            # Выключенная галка убирает ТОЛЬКО её: переход дальше обязан остаться.
            assert "rate" in button_ids(off), score_changed

    def test_skip_setting_defaults_to_shown(self):
        """Умолчание — показывать: настройки может не быть вовсе."""
        card = build_card(make_session(show_answer=True, settings={}), make_word(),
                          show_answer=True)
        assert "toggle_skip" in button_ids(card)

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
    """
    Однокоренные больше НЕ обрезаются по прогрессу — строки дальше пройденного
    остаются на месте и помечаются, а гасит их клиент.

    Обрезка стоила слишком дорого: у «знаю» из двенадцати форм парадигмы на
    экран попадала одна, у «хочу» — ни одной. Блок был, глагольной парадигмы в
    нём не было. Класс оставлен под тем же именем, но проверяет обратное.
    """

    def _word_with_refs(self, refs: str):
        w = make_word()
        w["references"] = refs
        return w

    def _rows(self, refs: str, studied: int):
        session = make_session(settings={"show_references": True})
        session["words_studied"] = studied
        card = build_card(session, self._word_with_refs(refs), show_answer=True)
        for item in card["extra_content"]:
            if item["type"] == "extra" and item.get("group") == "references":
                return item["rows"]
        return []

    def test_every_line_survives_regardless_of_progress(self):
        refs = ("<b>ידע</b>: <i>слов: 3</i>\n"
                "<i>[#5]</i>אָלֶף [a] пять\n"
                "<i>[#100]</i>בֵּית [b] сто\n"
                "<i>[#20]</i>גִּימֶל [g] двадцать")
        rows = self._rows(refs, studied=25)
        assert [r["rank"] for r in rows] == [5, 100, 20]

    def test_lines_beyond_progress_are_marked_not_removed(self):
        refs = ("<b>ידע</b>: <i>слов: 3</i>\n"
                "<i>[#5]</i>אָלֶף [a] пять\n"
                "<i>[#100]</i>בֵּית [b] сто\n"
                "<i>[#20]</i>גִּימֶל [g] двадцать")
        rows = self._rows(refs, studied=25)
        assert [(r["rank"], r["studied"]) for r in rows] == [(5, True), (100, False), (20, True)]

    def test_a_block_of_only_unreached_words_still_appears(self):
        """
        Раньше такой блок исчезал целиком: все строки вырезались. Именно так и
        пропадала парадигма у частотного глагола, все формы которого стоят
        дальше по списку.
        """
        refs = "<b>ידע</b>: <i>слов: 1</i>\n<i>[#999]</i>תָּו [t] тысяча"
        rows = self._rows(refs, studied=10)
        assert [(r["rank"], r["studied"]) for r in rows] == [(999, False)]

    def test_zero_progress_marks_everything_studied(self):
        """Счётчика ещё нет — гасить весь блок целиком незачем."""
        refs = "<b>ידע</b>: <i>слов: 1</i>\n<i>[#100]</i>בֵּית [b] сто"
        rows = self._rows(refs, studied=0)
        assert all(r["studied"] for r in rows)


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


# ── offline action semantics (for the Android offline "dumb player") ─────────────
# The bundle stamps each button/option with what an offline client should do, so
# Android carries no business rules of its own. These assert the single source of
# truth lives here in build_card.

def _btn(card, bid):
    return next(b for b in card["buttons"] if b["id"] == bid)


def test_before_answer_buttons_carry_offline_semantics():
    card = build_card(make_session(show_answer=False), make_word(), show_answer=False)
    know = _btn(card, "know")
    # «Знаю» записывает оценку и показывает ответ, НЕ листая дальше — как онлайн
    # know_word(). С submit офлайн-клиент перебрасывал сразу на следующее слово,
    # и карточка с переводом не показывалась вовсе.
    assert know["offline_effect"] == "record_and_reveal"
    assert know["offline_rating"] == "know"
    show = _btn(card, "show_answer")
    assert show["offline_effect"] == "reveal_answer"
    assert "offline_rating" not in show
    # Офлайн-семантику «Пропускать» проверяем на ответной стороне: там она
    # теперь и живёт.
    back = build_card(make_session(show_answer=True), make_word(), show_answer=True)
    skip = _btn(back, "toggle_skip")
    assert skip["offline_effect"] == "submit"
    assert skip["offline_rating"] == "skip"


def test_after_answer_score_changed_buttons_offline_semantics():
    card = build_card(make_session(show_answer=True, score_changed=True),
                      make_word(), show_answer=True)
    rate = _btn(card, "rate")
    # Оценку уже записала кнопка know — здесь только переход, иначе результат
    # уйдёт в outbox дважды.
    assert rate["offline_effect"] == "advance"
    assert "offline_rating" not in rate
    reconsider = _btn(card, "reconsider")
    assert reconsider["offline_effect"] == "reveal_question"
    # Без сети отменить записанное «знаю» можно только дописав в очередь более
    # поздний ответ: сервер применяет их по времени, и последний перекрывает
    # прежний. Прежде оценки здесь не было, и офлайн отменить было нечем.
    assert reconsider["offline_rating"] == "dont_know"


def test_after_answer_unchanged_rate_records_dont_know_offline():
    card = build_card(make_session(show_answer=True, score_changed=False),
                      make_word(), show_answer=True)
    rate = _btn(card, "rate")
    assert rate["offline_effect"] == "submit"
    assert rate["offline_rating"] == "dont_know"


def test_pick_options_carry_offline_rating():
    session = make_session(show_answer=False)
    session["pick_mode_active"] = True
    session["quiz_options"] = {
        "target_modality": "foreign",
        "options": [
            {"word_id": "w1", "target_text": "a", "is_correct": False},
            {"word_id": "w2", "target_text": "b", "is_correct": True},
            {"word_id": "w3", "target_text": "c", "is_correct": False},
        ],
    }
    card = build_card(session, make_word(), show_answer=False)
    po = card["pick_options"]
    assert po is not None
    ratings = {o["word_id"]: o["offline_rating"] for o in po["options"]}
    assert ratings["w1"] == "dont_know"
    assert ratings["w2"] == "know"
    assert ratings["w3"] == "dont_know"

def test_reconsider_is_offered_after_a_correct_pick_answer():
    """
    Регрессия: в пик-режиме верный ответ прятал «Ой, все-таки не знаю».

    Слово при этом засчитывалось знакомым и интервал повторения растягивался,
    а отменить это было нечем. Угадать один вариант из N легко, поэтому отмена
    там нужна не меньше, чем при обычном вводе.
    """
    session = make_session(show_answer=True, score_changed=True)
    session["pick_answer_was_used"] = True
    card = build_card(session, make_word(), show_answer=True)

    ids = [b["id"] for b in card["buttons"]]
    assert "reconsider" in ids, f"кнопка отмены пропала в пик-режиме: {ids}"

    reconsider = _btn(card, "reconsider")
    assert reconsider["offline_effect"] == "reveal_question"


def test_reconsider_absent_when_the_word_was_not_scored_as_known():
    """После «Не знаю» отменять нечего — слово и так засчитано незнакомым."""
    card = build_card(make_session(show_answer=True, score_changed=False),
                      make_word(), show_answer=True)
    assert "reconsider" not in [b["id"] for b in card["buttons"]]

def test_prompt_shows_only_the_primary_meaning_of_a_homograph():
    """
    У омографов перевод многострочный: основное значение плюс строка про другое
    чтение. В вопросе её показывать нельзя — там стоит вторая огласовка, и
    подсказка выдала бы ответ.
    """
    from app.services.card_builder import primary_meaning

    full = "инстинкт, влечение\n⚠ то же написание читается иначе: יָצַר (яцАр) — создал"
    assert primary_meaning(full) == "инстинкт, влечение"

    word = make_word()
    word["translation"] = full
    session = make_session(show_answer=False)
    session["show_mode"] = "translation"
    card = build_card(session, word, show_answer=False)

    shown = " ".join(c["text"] for c in card["content"] if c["type"] == "translation")
    assert "инстинкт" in shown
    assert "יָצַר" not in shown, "вторая огласовка не должна попадать в вопрос"
    assert "читается иначе" not in shown


def test_answer_side_keeps_the_other_reading():
    """А на ответной стороне другое чтение показать наоборот нужно — это и учим."""
    word = make_word()
    word["translation"] = "инстинкт, влечение\n⚠ то же написание читается иначе: יָצַר (яцАר) — создал"
    card = build_card(make_session(show_answer=True), word, show_answer=True)

    shown = " ".join(c["text"] for c in card["content"] if c["type"] == "translation")
    assert "читается иначе" in shown, "полный перевод с вариантами должен остаться"


def test_pick_option_uses_the_primary_meaning_only():
    """Вариант ответа в пик-режиме — короткий, без пометки о другом чтении."""
    from app.services.quiz_service import _get_text_for_modality

    word = {"translation": "грош (монета)\n⚠ то же написание читается иначе: גָּרוּשׁ (гарУш) — разведённый"}
    assert _get_text_for_modality(word, "translation") == "грош (монета)"

def test_extra_block_labels_depend_on_the_language():
    """
    Поля tones/references заводились под китайский, но переиспользуются: у
    иврита огласовка играет роль тонов, а однокоренные — роль ссылок на слова
    из тех же иероглифов. Подпись блока обязана следовать языку, иначе учащийся
    читает «Тоны» над списком огласовок.
    """
    from app.services.card_builder import _extra_label

    assert _extra_label("Китайский", "tones") == "🎵 Тоны:"
    assert _extra_label("Китайский", "references") == "🔍 Ссылки:"
    assert "огласовк" in _extra_label("Иврит", "tones")
    assert "основой" in _extra_label("Иврит", "references")
    # Незнакомый язык не должен ронять сборку карточки.
    assert _extra_label("Суахили", "tones") == "🎵 Тоны:"
    assert _extra_label("", "radicals") == "🔍 Радикалы:"


def test_language_lookup_survives_renaming():
    """
    Название языка редактируется администратором, а промах по ключу отказывает
    молча: изучающий иврит просто увидит «Тоны:» над списком огласовок и вряд ли
    поймёт, что это сбой. Поэтому регистр и пробелы значения иметь не должны.
    """
    from app.services.card_builder import _extra_label

    for name in ("иврит", "ИВРИТ", "  Иврит  ", "иВрИт"):
        assert "огласовк" in _extra_label(name, "tones"), name
        assert "основой" in _extra_label(name, "references"), name


def test_hebrew_card_labels_its_extra_blocks_in_hebrew_terms():
    word = make_word()
    word["references"] = "<b>את</b>: <i>слов с этой основой: 2</i>\n<i>[#1]</i>אֵת [ʔet] знак"
    session = make_session(show_answer=True)
    session["language_name_ru"] = "Иврит"
    session["settings"]["show_references"] = True
    session["words_studied"] = 100

    card = build_card(session, word, show_answer=True)
    labels = [e["text"] for e in card["extra_content"] if e["type"] == "label"]
    assert any("основой" in t for t in labels), labels
    assert not any("Ссылки" in t for t in labels), labels


def test_grammar_note_shows_part_of_speech_and_a_differing_lemma():
    from app.services.card_builder import _grammar_note

    assert _grammar_note({"part_of_speech": "глаг", "lemma": "ידע",
                          "word_foreign": "יוֹדֵעַ"}) == "глагол · словарная форма: ידע"
    # Совпадающая лемма — шум, её не показываем.
    assert _grammar_note({"part_of_speech": "сущ", "lemma": "כן",
                          "word_foreign": "כֵּן"}) == "существительное"
    assert _grammar_note({}) == ""


# ── кнопки пик-режима ────────────────────────────────────────────────────────

def _pick_session(show_skip=True):
    session = make_session(show_answer=False,
                           settings={"show_sounds": True, "show_skip_button": show_skip})
    session["pick_mode_active"] = True
    session["quiz_options"] = {
        "target_modality": "translation",
        "options": [{"word_id": "w1", "target_text": "книга", "is_correct": True},
                    {"word_id": "w2", "target_text": "лошадь", "is_correct": False}],
    }
    return session


def test_pick_mode_sends_its_own_buttons():
    """
    Раньше в пик-режиме карточка отдавала обычные know/show_answer/skip, а каждый
    клиент выбрасывал buttons[] целиком и рисовал свою «❓ Не знаю». Правило
    жило в трёх копиях, и вместе с массивом терялась «Пропускать».
    """
    word = make_word()
    word["user_word_data"] = {"is_skipped": False}
    card = build_card(_pick_session(), word, show_answer=False)

    ids = [b["id"] for b in card["buttons"]]
    assert ids == ["pick_dont_know"], ids
    assert "know" not in ids and "show_answer" not in ids


def test_pick_mode_shows_only_dont_know_next_to_the_options():
    """
    Рядом с вариантами — только «Не знаю». «Пропускать» здесь не место: решение
    исключить слово принимают, увидев его целиком, а на вопросной стороне нет
    ни перевода, ни произношения.
    """
    word = make_word()
    word["user_word_data"] = {"is_skipped": False}

    for show_skip in (True, False):
        card = build_card(_pick_session(show_skip=show_skip), word, show_answer=False)
        assert [b["id"] for b in card["buttons"]] == ["pick_dont_know"], show_skip


def test_pick_dont_know_records_the_answer_offline():
    """
    Это pick_answer с dont_know, а не show_answer: незнание ЗАСЧИТЫВАЕТСЯ.
    Перепутав их, офлайн-клиент потерял бы оценку — show_answer ничего не пишет.
    """
    word = make_word()
    word["user_word_data"] = {"is_skipped": False}
    card = build_card(_pick_session(), word, show_answer=False)

    btn = next(b for b in card["buttons"] if b["id"] == "pick_dont_know")
    assert btn["offline_effect"] == "record_and_reveal"
    assert btn["offline_rating"] == "dont_know"


def test_skip_lives_on_the_answer_side_only():
    """
    «Пропускать» — на экране ответа и всегда (когда настройка включена). На
    вопросной стороне её быть не должно ни в обычном режиме, ни в пик-режиме:
    она появлялась то там, то тут (пик-режим включается случайно) и выглядела
    как зависящая от прошлого ответа.
    """
    word = make_word()
    word["user_word_data"] = {"is_skipped": False}

    for session in (make_session(show_answer=False), _pick_session()):
        front = build_card(session, word, show_answer=False)
        assert "toggle_skip" not in [b["id"] for b in front["buttons"]]

    for score_changed in (True, False):
        s = make_session(show_answer=True)
        s["session_score_changed"] = score_changed
        back = build_card(s, word, show_answer=True)
        assert "toggle_skip" in [b["id"] for b in back["buttons"]], score_changed


def test_skip_state_is_visible_on_the_answer_side():
    word = make_word()
    word["user_word_data"] = {"is_skipped": True}
    card = build_card(make_session(show_answer=True), word, show_answer=True)

    skip = next(b for b in card["buttons"] if b["id"] == "toggle_skip")
    assert skip["text"] == "⏩ Не пропускать"


def test_ban_combination_button_only_after_a_misleading_option():
    """
    Запрещать имеет смысл конкретный вариант, который сбил с толку. После
    верного ответа такого нет, и после «не знаю» тоже — там никто не путал.
    """
    from app.services.card_builder import _buttons_after

    misled = [b["id"] for b in _buttons_after(False, False, True, "w-2")]
    assert "ban_pair" in misled
    ban = next(b for b in _buttons_after(False, False, True, "w-2") if b["id"] == "ban_pair")
    assert ban["bad_word_id"] == "w-2"

    for no_target in (None, ""):
        assert "ban_pair" not in [b["id"] for b in _buttons_after(False, False, True, no_target)]


def test_answer_side_of_pick_mode_keeps_the_normal_buttons():
    """После ответа пик-режим кончился — кнопки снова обычные."""
    word = make_word()
    word["user_word_data"] = {"is_skipped": False}
    card = build_card(_pick_session(), word, show_answer=True)

    ids = [b["id"] for b in card["buttons"]]
    assert "pick_dont_know" not in ids
    assert card["pick_options"] is None

# ── блок доп. информации разбирается в строки таблицы ────────────────────────

def test_extra_blocks_are_parsed_into_table_rows():
    """
    Клиенты рисуют таблицу, а не текст: иврит и русский в одной строке уводили
    весь блок вправо, потому что направление абзаца берётся по первому сильному
    символу. Разбор здесь, а не в трёх клиентах — иначе это три копии знания об
    одном формате, а такие копии в этом проекте уже дважды расходились.
    """
    from app.services.card_builder import _extra_rows

    refs = _extra_rows("<b>את</b>: <i>слов с этой основой: 15</i>\n"
                       "<i>[#28]</i>אוֹתְךָ [ʔotˈχa] тебя\n"
                       "<i>[#33]</i>אוֹתִי [ʔoˈti] меня")
    assert "слов с этой основой" in refs["header"]
    # rank рядом с marker: по нему решается, дошёл ли человек до этого слова,
    # и клиент гасит непройденную строку. Из текста «[#28]» это каждый раз
    # выковыривали бы заново.
    # Слово и транскрипция — РАЗНЫЕ ячейки: колонки те же, что у таблицы тегов
    # на той же карточке, иначе две соседние таблицы выглядят по-разному.
    assert refs["rows"] == [
        {"marker": "[#28]", "rank": 28, "foreign": "אוֹתְךָ", "ipa": "ʔotˈχa", "ru": "тебя"},
        {"marker": "[#33]", "rank": 33, "foreign": "אוֹתִי", "ipa": "ʔoˈti", "ru": "меня"},
    ]

    # Номер у варианта огласовки теперь есть — но только там, где этот вариант
    # сам есть в словаре. Просьба владельца: «таблица вариантов огласовки,
    # первый столбец пустой — добавить номера слова». У второй огласовки тех же
    # согласных своего номера часто нет: עַם «народ» в десятитысячник не
    # входит, и ячейка остаётся пустой, как была.
    tones = _extra_rows("<b>עם</b>: <i>вариантов огласовки: 2</i>\n"
                        " - <i>[#15]</i><b>עִם</b> [ʔim]: с, вместе с\n"
                        " - <b>עַם</b> [ʔam]: народ")
    assert "вариантов огласовки" in tones["header"]
    assert tones["rows"] == [
        {"marker": "[#15]", "rank": 15, "foreign": "עִם", "ipa": "ʔim", "ru": "с, вместе с"},
        {"marker": "", "rank": None, "foreign": "עַם", "ipa": "ʔam", "ru": "народ"},
    ]


def test_unparsed_line_is_kept_not_dropped():
    """
    Строку незнакомой формы теряем только через мой недосмотр — поэтому она
    попадает в русскую ячейку целиком. Молча выбросить кусок словаря хуже, чем
    показать его неровно.
    """
    from app.services.card_builder import _extra_rows

    d = _extra_rows("заголовок\nсовсем другая строка")
    assert d["header"] == "заголовок"
    assert d["rows"] == [{"marker": "", "foreign": "", "ipa": "", "ru": "совсем другая строка"}]


def test_card_carries_rows_for_hebrew_extras():
    word = make_word()
    word["tones"] = ("<b>עם</b>: <i>вариантов огласовки: 2</i>\n"
                     " - <b>עִם</b> [ʔim]: с, вместе с\n"
                     " - <b>עַם</b> [ʔam]: народ")
    session = make_session(show_answer=True)
    session["language_name_ru"] = "Иврит"
    session["settings"]["show_tones"] = True
    session["words_studied"] = 100

    card = build_card(session, word, show_answer=True)
    block = next(e for e in card["extra_content"]
                 if e["type"] == "extra" and e.get("group") == "tones")
    assert len(block["rows"]) == 2
    assert block["rows"][0]["foreign"] == "עִם"
    assert block["rows"][0]["ipa"] == "ʔim"
    # Исходный текст остаётся: по нему рисуют старые офлайн-партии.
    assert block["text"].strip()

def test_header_is_split_into_the_same_columns():
    """
    «<b>עם</b>: вариантов огласовки: 2» — тоже двуязычная строка, и отдельной
    строкой она уезжала вправо по первой ивритской букве, как и остальные до
    таблицы. Режем на те же две колонки.
    """
    from app.services.card_builder import _extra_rows

    d = _extra_rows("<b>את</b>: <i>слов с этой основой: 15</i> <i>(показаны первые 12)</i>\n"
                    "<i>[#28]</i>אוֹתְךָ [ʔotˈχa] тебя")
    assert d["header_foreign"] == "<b>את</b>"
    assert d["header_ru"] == "слов с этой основой: 15 (показаны первые 12)"
    # Целый заголовок остаётся: по нему рисуют старые офлайн-партии.
    assert d["header"].startswith("<b>את</b>")


def test_header_without_the_expected_shape_is_kept_whole():
    from app.services.card_builder import _extra_rows

    d = _extra_rows("просто заголовок\n - <b>עִם</b> [ʔim]: с")
    assert d["header"] == "просто заголовок"
    assert d["header_foreign"] == "" and d["header_ru"] == ""



# ── теги: группы слов для совместного повторения ──────────────────────────────

TAG_GROUPS = [{
    "tag": "числительные",
    "label": "🔢 Числительные",
    "rows": [
        {"rank": 40, "ru": "один", "ipa": "ʔeˈχad", "foreign": "אֶחָד", "self": False},
        {"rank": 417, "ru": "три", "ipa": "ʃaˈloʃ", "foreign": "שָׁלוֹשׁ", "self": True},
        {"rank": 890, "ru": "десять", "ipa": "ˈʔeseʁ", "foreign": "עֶשֶׂר", "self": False},
    ],
}]


def _tag_extra(card):
    return [i for i in card["extra_content"] if i["type"] == "tag_group"]


def test_tag_group_reaches_the_card_after_the_answer():
    word = make_word(foreign="שָׁלוֹשׁ", translation="три")
    word["tag_groups"] = TAG_GROUPS
    card = build_card(make_session(show_answer=True), word, show_answer=True)

    blocks = _tag_extra(card)
    assert len(blocks) == 1, card["extra_content"]
    assert blocks[0]["tag"] == "числительные"
    assert [r["rank"] for r in blocks[0]["rows"]] == [40, 417, 890]
    # Подпись идёт отдельным элементом — так же, как у огласовок и однокоренных.
    labels = [i["text"] for i in card["extra_content"] if i["type"] == "label"]
    assert "🔢 Числительные" in labels


def test_tag_group_is_absent_before_the_answer():
    word = make_word()
    word["tag_groups"] = TAG_GROUPS
    card = build_card(make_session(), word, show_answer=False)
    assert _tag_extra(card) == []


def test_tag_group_is_not_trimmed_by_progress():
    """
    Однокоренные обрезаются по пройденному, а группа тега — нет: числовой ряд с
    дырами на месте непройденных чисел учить нельзя. Слово #890 стоит далеко за
    прогрессом, и оно обязано остаться.
    """
    word = make_word()
    word["tag_groups"] = TAG_GROUPS
    session = make_session(show_answer=True)
    session["words_studied"] = 50
    card = build_card(session, word, show_answer=True)
    assert [r["rank"] for r in _tag_extra(card)[0]["rows"]] == [40, 417, 890]


def test_the_current_word_is_marked_in_its_group():
    word = make_word()
    word["tag_groups"] = TAG_GROUPS
    card = build_card(make_session(show_answer=True), word, show_answer=True)
    marked = [r["rank"] for r in _tag_extra(card)[0]["rows"] if r.get("self")]
    assert marked == [417]


def test_a_word_without_tags_gets_no_block():
    card = build_card(make_session(show_answer=True), make_word(), show_answer=True)
    assert _tag_extra(card) == []


def test_empty_group_is_skipped():
    """Пустая рамка на месте группы — тоже дефект: место занято, смысла нет."""
    word = make_word()
    word["tag_groups"] = [{"tag": "пустая", "label": "пусто", "rows": []}]
    card = build_card(make_session(show_answer=True), word, show_answer=True)
    assert _tag_extra(card) == []
    assert "пусто" not in [i.get("text") for i in card["extra_content"]]


def test_tag_group_can_be_switched_off():
    """
    У огласовок и однокоренных переключатель есть, а у групп не было: блок
    показывался всегда. Числительные это 21 строка — кому-то на карточке лишняя.
    """
    word = make_word()
    word["tag_groups"] = TAG_GROUPS
    session = make_session(show_answer=True, settings={"show_sounds": True, "show_tags": False})
    card = build_card(session, word, show_answer=True)
    assert _tag_extra(card) == []


def test_tag_group_is_shown_when_the_setting_is_absent():
    """Старые настройки без ключа не должны прятать блок."""
    word = make_word()
    word["tag_groups"] = TAG_GROUPS
    session = make_session(show_answer=True, settings={"show_sounds": True})
    card = build_card(session, word, show_answer=True)
    assert len(_tag_extra(card)) == 1


def test_rows_beyond_progress_are_marked_unstudied():
    """
    В группе видно весь набор, включая непройденное, — иначе числовой ряд
    учить нельзя. Но человек должен различать, докуда дошёл: непройденные
    строки клиент гасит серым, а признак считает сервер.
    """
    word = make_word()
    word["tag_groups"] = TAG_GROUPS          # ранги 40, 417, 890
    session = make_session(show_answer=True)
    session["words_studied"] = 500
    rows = _tag_extra(build_card(session, word, show_answer=True))[0]["rows"]
    assert [(r["rank"], r["studied"]) for r in rows] == [(40, True), (417, True), (890, False)]


def test_without_progress_nothing_is_greyed_out():
    """Ноль пройденных — счётчика ещё нет, и гасить всю группу целиком незачем."""
    word = make_word()
    word["tag_groups"] = TAG_GROUPS
    session = make_session(show_answer=True)
    session["words_studied"] = 0
    rows = _tag_extra(build_card(session, word, show_answer=True))[0]["rows"]
    assert all(r["studied"] for r in rows)


# ── однокоренные: показываем всё, непройденное гасим ──────────────────────────

REFS = ("<b>ידע</b>: <i>слов с этой основой: 3</i>\n"
        "<i>[#54]</i>יוֹדַעַת [joˈdaat] знаю, знает (ж)\n"
        "<i>[#178]</i>לָדַעַת [laˈdaat] знать, узнать\n"
        "<i>[#330]</i>יָדַעְתִּי [jaˈdaʔti] я знал")


def _refs_rows(card):
    for item in card["extra_content"]:
        if item["type"] == "extra" and item.get("group") == "references":
            return item["rows"]
    return []


def test_the_whole_paradigm_is_shown_not_just_what_you_reached():
    """
    Раньше строки дальше прогресса вырезались, и от глагольной парадигмы почти
    ничего не оставалось: у «знаю» из двенадцати форм видна была одна, у
    «хочу» — ни одной. Парадигма существовала, но увидеть её было нельзя.
    """
    word = make_word()
    word["references"] = REFS
    session = make_session(show_answer=True, settings={"show_sounds": True, "show_references": True})
    session["words_studied"] = 100
    rows = _refs_rows(build_card(session, word, show_answer=True))
    assert [r["rank"] for r in rows] == [54, 178, 330]


def test_rows_beyond_progress_are_marked_instead_of_cut():
    word = make_word()
    word["references"] = REFS
    session = make_session(show_answer=True, settings={"show_sounds": True, "show_references": True})
    session["words_studied"] = 100
    rows = _refs_rows(build_card(session, word, show_answer=True))
    assert [(r["rank"], r["studied"]) for r in rows] == [(54, True), (178, False), (330, False)]


def test_a_row_without_a_number_counts_as_studied():
    """
    Строку без номера погасить не за что: у огласовок номеров нет вовсе, и
    гасить их целиком было бы хуже, чем не гасить.
    """
    word = make_word()
    word["references"] = "<b>ידע</b>: <i>слов: 1</i>\nстрока без номера"
    session = make_session(show_answer=True, settings={"show_sounds": True, "show_references": True})
    session["words_studied"] = 10
    rows = _refs_rows(build_card(session, word, show_answer=True))
    assert all(r["studied"] for r in rows)


def test_vocalisation_variants_are_never_hidden_by_progress():
    """
    Вариант огласовки показывается всегда, даже если до того слова не дошли.

    У строк вариантов появился номер — и вместе с ним искушение гасить их так
    же, как однокоренные. Делать этого нельзя: второй вариант огласовки — это
    предупреждение «то же написание читается иначе». Спрятав его до того, как
    человек дойдёт до того слова, карточка умолчала бы ровно о том, ради чего
    блок и заведён: о том, что он читает не то, что написано.
    """
    from app.services.card_builder import _extra_rows, _mark_studied

    tones = _extra_rows("<b>לך</b>: <i>вариантов огласовки: 2</i>\n"
                        " - <i>[#11]</i><b>לְךָ</b> [leˈχa]: тебе (м)\n"
                        " - <i>[#9514]</i><b>לָךְ</b> [laχ]: тебе (ж)")
    assert [r["rank"] for r in tones["rows"]] == [11, 9514]
    # Сам разбор отметок не ставит — их ставит отдельный проход, и к блоку
    # вариантов он не применяется.
    assert all("studied" not in r for r in tones["rows"])

    # А если бы применялся, строка №9514 погасла бы: вот что мы не делаем.
    marked = _mark_studied(dict(tones), words_studied=100)
    assert [r.get("studied") for r in marked["rows"]] == [True, False]


def test_the_transcription_field_holds_only_the_international_form():
    """
    В транскрипции — только международная запись, русская внизу отдельно.

    Просьба владельца: «сейчас прямо в одном поле записан международный вариант
    и просто звучание на русском; для начального этапа это было хорошо, сейчас
    надо оставить только международный стандарт; можно ли сохранить русский
    где-нибудь в экстра инфо?». Можно — поэтому не выбрасываем, а переносим.
    """
    from app.services.card_builder import build_card

    word = {
        "_id": "x", "word_number": 240, "word_foreign": "אָחִי",
        "translation": "мой брат", "transcription": "/ʔaˈχi/",
        "transcription_ru": "ахИ",
    }
    session = {"words": [], "current_index": 0, "settings": {},
               "words_studied": 241, "language_name_ru": "Иврит"}
    card = build_card(session, word, show_answer=True)

    shown = [i["text"] for i in card["content"] if i["type"] == "transcription"]
    assert shown == ["[/ʔaˈχi/]"], shown
    assert all("ахИ" not in t for t in shown), "русское звучание осталось в транскрипции"

    extra = [i.get("text") for i in card["extra_content"]]
    assert "ахИ" in extra, f"русское звучание потерялось совсем: {extra}"
    assert any("русскими буквами" in str(t) for t in extra), extra


def test_a_word_without_the_russian_sounding_gets_no_empty_block():
    """Пустого блока с подписью и ничем внутри быть не должно."""
    from app.services.card_builder import build_card

    word = {"_id": "x", "word_number": 1, "word_foreign": "אֵת",
            "translation": "вот", "transcription": "/ʔet/"}
    card = build_card({"words": [], "current_index": 0, "settings": {},
                       "words_studied": 1, "language_name_ru": "Иврит"},
                      word, show_answer=True)
    assert not any("русскими буквами" in str(i.get("text")) for i in card["extra_content"])


# ── упрощённое написание и примеры для чтения ───────────────────────────────
#
# Две задачи владельца, сделанные вместе, потому что обе живут в одной карточке.
#
# ОГЛАСОВКА. «Реальные тексты без огласовок. Нужен промежуточный этап — когда
# огласовка быстро включается по простому нажатию.» Значит на карточку едут ОБЕ
# формы: карточки пререндерятся в офлайн-партию, и форма, которой в партии нет,
# в офлайне не появится никогда, сколько ни нажимай.
#
# ЧТЕНИЕ. Разбор Крашена сводится к тому, что язык усваивается из понятного
# ввода. Отдельное слово ввода не образует — нужна фраза, понятная целиком.
# Предложения собраны заранее только из пройденных слов (words/reading).

СЛОВО_С_ОГЛАСОВКОЙ = {
    "word_foreign": "זְמַן",
    "word_foreign_simple": "זמן",
    "translation": "время",
    "word_number": 87,
}


def _карточка(word, settings, show_answer=True):
    from app.services.card_builder import build_card
    сессия = {"settings": settings, "language_name_ru": "Иврит", "words_studied": 300}
    return build_card(сессия, dict(word, user_word_data={}), show_answer=show_answer)


def _элемент(card, тип):
    for c in card["content"]:
        if c["type"] == тип:
            return c
    return None


def test_обе_формы_написания_едут_в_карточке():
    """Переключать нечего, если вторая форма осталась на сервере."""
    c = _элемент(_карточка(СЛОВО_С_ОГЛАСОВКОЙ, {"show_simplified": True}), "foreign")
    assert c["text_simple"] == "זמן"
    assert c["text_full"] == "זְמַן"


def test_галка_решает_какая_форма_первой():
    вкл = _элемент(_карточка(СЛОВО_С_ОГЛАСОВКОЙ, {"show_simplified": True}), "foreign")
    выкл = _элемент(_карточка(СЛОВО_С_ОГЛАСОВКОЙ, {"show_simplified": False}), "foreign")
    assert вкл["text"] == "זמן", "галка включена — показываем упрощённое"
    assert выкл["text"] == "זְמַן", "галка выключена — показываем огласованное"
    # Обе формы приходят в любом случае: переключение клиентское.
    assert выкл["text_simple"] == "זמן"


def test_без_второй_формы_переключателя_нет():
    """
    Английское слово или ивритское без огласовки. Отдать вторую форму значило
    бы показать иконку, которая ничего не меняет.
    """
    c = _элемент(_карточка({"word_foreign": "time", "translation": "время",
                            "word_number": 60}, {"show_simplified": True}), "foreign")
    assert c["text"] == "time"
    assert "text_simple" not in c and "text_full" not in c


def test_совпадающие_формы_переключателем_не_считаются():
    """У двух слов иврита огласовки нет вовсе — формы равны, иконка не нужна."""
    c = _элемент(_карточка({"word_foreign": "מי", "word_foreign_simple": "מי",
                            "translation": "кто", "word_number": 53},
                           {"show_simplified": True}), "foreign")
    assert "text_simple" not in c


def test_вопросная_сторона_тоже_знает_обе_формы():
    """Слово спрашивают — и спрашивать надо той же формой, что показывают."""
    c = _элемент(_карточка(СЛОВО_С_ОГЛАСОВКОЙ, {"show_simplified": True},
                           show_answer=False), "foreign")
    assert c["text"] == "זמן" and c["text_full"] == "זְמַן"


def test_крупное_написание_идёт_теми_же_формами():
    """Иначе на одном экране окажутся две разные записи одного слова."""
    card = _карточка(СЛОВО_С_ОГЛАСОВКОЙ, {"show_simplified": True, "show_big": True})
    assert card["big_word"]["word"] == "זמן"
    assert card["big_word"]["word_full"] == "זְמַן"


ТРИ_ПРЕДЛОЖЕНИЯ = [
    {"text": "יש זמן", "ru": "Время есть."},
    {"text": "זמן טוב", "ru": "Хорошее время."},
    {"text": "אין יותר זמן", "ru": "Больше нет времени."},
]


def _чтение(card):
    return [i for i in card["extra_content"] if i.get("group") == "reading"]


def test_примеры_для_чтения_попадают_на_карточку():
    слово = dict(СЛОВО_С_ОГЛАСОВКОЙ, reading_sentences=ТРИ_ПРЕДЛОЖЕНИЯ)
    блоки = _чтение(_карточка(слово, {"show_reading": True}))
    assert [b["type"] for b in блоки] == ["label", "reading"]
    assert "чтения" in блоки[0]["text"]


def test_перевод_стоит_отдельной_строкой_под_предложением():
    """
    Владелец: «сначала иностранный, следующей строкой русский — чтобы перевод
    не был виден вместе с текстом». Одной строкой перевод стоял бы рядом.
    """
    слово = dict(СЛОВО_С_ОГЛАСОВКОЙ, reading_sentences=ТРИ_ПРЕДЛОЖЕНИЯ)
    rows = _чтение(_карточка(слово, {"show_reading": True}))[1]["rows"]
    assert len(rows) == 2 * len(ТРИ_ПРЕДЛОЖЕНИЯ)
    assert rows[0]["foreign"] == "יש זמן" and rows[0]["ru"] == ""
    assert rows[1]["ru"] == "Время есть." and rows[1]["foreign"] == ""
    # Номер — только у иностранной строки: повтор читался бы как ещё пример.
    assert rows[0]["marker"] == "1" and rows[1]["marker"] == ""


def test_галка_выключает_примеры():
    слово = dict(СЛОВО_С_ОГЛАСОВКОЙ, reading_sentences=ТРИ_ПРЕДЛОЖЕНИЯ)
    assert _чтение(_карточка(слово, {"show_reading": False})) == []


def test_до_ответа_примеров_нет():
    """Предложения содержат само слово — до ответа это подсказка."""
    слово = dict(СЛОВО_С_ОГЛАСОВКОЙ, reading_sentences=ТРИ_ПРЕДЛОЖЕНИЯ)
    assert _чтение(_карточка(слово, {"show_reading": True}, show_answer=False)) == []


def test_без_предложений_блока_нет():
    """Пустая подпись «Примеры для чтения:» без примеров хуже, чем ничего."""
    assert _чтение(_карточка(СЛОВО_С_ОГЛАСОВКОЙ, {"show_reading": True})) == []


def test_из_большого_запаса_показываются_только_пять():
    """Запас может дорасти до десяти; показывать все — утопить карточку."""
    много = [{"text": f"משפט {i}", "ru": f"Фраза {i}"} for i in range(10)]
    слово = dict(СЛОВО_С_ОГЛАСОВКОЙ, reading_sentences=много)
    rows = _чтение(_карточка(слово, {"show_reading": True}))[1]["rows"]
    assert len(rows) == 10, "пять предложений по две строки"
    тексты = {r["foreign"] for r in rows if r["foreign"]}
    assert len(тексты) == 5 and тексты <= {м["text"] for м in много}
