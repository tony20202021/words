"""Unit tests for study router helper functions: _prepare_card.

Note: reference filtering by [#N] was moved to BLS card_builder._filter_refs —
see business_logic_service/tests/test_card_builder.py::TestReferencesFiltering.
_prepare_card now only reorders extra_content groups (no words_studied param).
"""

import pytest
from app.routers.study import _prepare_card


# ── _prepare_card: sorting ─────────────────────────────────────────────────────

class TestPrepareCardSorting:
    def _make_card(self, groups):
        extra = []
        for g in groups:
            extra.append({"type": "label", "text": f"Label {g}", "group": g})
            extra.append({"type": "extra", "text": f"Content {g}", "group": g})
        return {"extra_content": extra}

    def test_radicals_before_references_before_tones(self):
        card = self._make_card(["tones", "references", "radicals"])
        _prepare_card(card)
        groups = [i["group"] for i in card["extra_content"]]
        assert groups == ["radicals", "radicals", "references", "references", "tones", "tones"]

    def test_already_correct_order_unchanged(self):
        card = self._make_card(["radicals", "references", "tones"])
        _prepare_card(card)
        groups = [i["group"] for i in card["extra_content"]]
        assert groups == ["radicals", "radicals", "references", "references", "tones", "tones"]

    def test_missing_group_appended_at_end(self):
        card = self._make_card(["tones", "custom"])
        _prepare_card(card)
        groups_seen = [i["group"] for i in card["extra_content"] if i["type"] == "label"]
        assert groups_seen[-1] == "custom"

    def test_empty_extra_content_no_change(self):
        card = {"extra_content": []}
        _prepare_card(card)
        assert card["extra_content"] == []
        assert card["extra_groups"] == []

    def test_no_extra_content_key_no_error(self):
        card = {}
        _prepare_card(card)
        assert card["extra_groups"] == []

    def test_extra_groups_split_by_group(self):
        card = self._make_card(["radicals", "references", "tones"])
        _prepare_card(card)
        assert len(card["extra_groups"]) == 3
        assert [g["group"] for g in card["extra_groups"]] == ["radicals", "references", "tones"]
        assert len(card["extra_groups"][0]["items"]) == 2

    def test_references_text_not_modified_by_prepare_card(self):
        """_prepare_card no longer filters references — BLS handles that."""
        card = {
            "extra_content": [
                {"type": "label", "text": "Ссылки:", "group": "references"},
                {"type": "extra", "text": "<i>[#526]</i>词 A\n<i>[#9999]</i>词 B",
                 "group": "references"},
            ]
        }
        _prepare_card(card)
        extra_text = next(i["text"] for i in card["extra_content"] if i["type"] == "extra")
        # both lines preserved — filtering is done by BLS before this point
        assert "[#526]" in extra_text
        assert "[#9999]" in extra_text
