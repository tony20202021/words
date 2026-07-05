"""
Tests for UTC-based day boundary in word scheduling and session expiry.

The system uses UTC midnight as the day boundary so that users in UTC+3 (Moscow)
can study past midnight local time without the word list changing unexpectedly.
The effective "day change" for Moscow users is at 03:00 MSK (= 00:00 UTC).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.word_service import _calculate_update
from app.services.session_service import is_session_expired, touch_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc(y, mo, d, h=0, mi=0, s=0) -> datetime:
    return datetime(y, mo, d, h, mi, s)


def _make_session(last_activity_utc: datetime, settings: dict = None) -> dict:
    return {
        "last_activity_at": last_activity_utc.isoformat(),
        "settings": settings or {},
    }


# ---------------------------------------------------------------------------
# _calculate_update: next_check_date must be UTC midnight
# ---------------------------------------------------------------------------

class TestNextCheckDateUsesUTC:
    def test_score1_sets_utc_midnight(self):
        """next_check_date for score=1 is midnight of UTC date, not local time."""
        fake_utc = _utc(2026, 7, 4, 21, 30)  # 00:30 Moscow July 5
        with patch("app.services.word_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = fake_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            result = _calculate_update({}, score=1, is_skipped=False)

        ncd = result["next_check_date"]
        # Should be UTC midnight of July 5 (interval=1 day from July 4 UTC)
        assert ncd == "2026-07-05T00:00:00"

    def test_score0_sets_todays_utc_midnight(self):
        """next_check_date for score=0 is today's UTC midnight (word reappears today)."""
        fake_utc = _utc(2026, 7, 4, 21, 30)  # 00:30 Moscow July 5, but UTC is still July 4
        with patch("app.services.word_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = fake_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            result = _calculate_update({}, score=0, is_skipped=False)

        ncd = result["next_check_date"]
        # Should be UTC midnight of July 4 (today in UTC even though Moscow is July 5)
        assert ncd == "2026-07-04T00:00:00"

    def test_score1_before_utc_midnight_still_today_utc(self):
        """At 02:30 Moscow (23:30 UTC), next_check_date is tomorrow UTC."""
        fake_utc = _utc(2026, 7, 3, 23, 30)  # 02:30 Moscow July 4, UTC still July 3
        with patch("app.services.word_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = fake_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            result = _calculate_update({}, score=1, is_skipped=False)

        ncd = result["next_check_date"]
        # Interval=1 day from July 3 UTC → July 4 UTC midnight
        assert ncd == "2026-07-04T00:00:00"

    def test_interval_doubling_uses_utc_base(self):
        """Interval doubling: base date is UTC now, not local time."""
        fake_utc = _utc(2026, 7, 4, 21, 0)  # 00:00 Moscow July 5
        existing = {"score": 1, "check_interval": 4, "next_check_date": "2026-07-04T00:00:00"}
        with patch("app.services.word_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = fake_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            result = _calculate_update(existing, score=1, is_skipped=False)

        # Interval doubles: 4 → 8 days from July 4 UTC = July 12 UTC midnight
        assert result["check_interval"] == 8
        assert result["next_check_date"] == "2026-07-12T00:00:00"


# ---------------------------------------------------------------------------
# is_session_expired: day boundary must be UTC midnight, not Moscow midnight
# ---------------------------------------------------------------------------

class TestSessionExpiryUsesUTC:
    def test_crossing_moscow_midnight_does_not_trigger_expiry(self):
        """Session active at 23:50 Moscow (20:50 UTC) should NOT expire at 00:10 Moscow (21:10 UTC).
        Both are still the same UTC date (July 4 UTC), so cal_days=0 and the session continues."""
        last = _utc(2026, 7, 4, 20, 50)  # 23:50 Moscow July 4
        session = _make_session(last)
        now_utc = _utc(2026, 7, 4, 21, 10)  # 00:10 Moscow July 5 (but still UTC July 4)

        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            expired = is_session_expired(session)

        assert not expired, "Session should NOT expire when Moscow crosses midnight but UTC date is unchanged"

    def test_crossing_utc_midnight_does_trigger_expiry_eventually(self):
        """Session from the day before UTC-wise should expire at 6 AM UTC (= 9 AM Moscow)."""
        last = _utc(2026, 7, 4, 20, 0)  # 23:00 Moscow July 4
        session = _make_session(last)
        # Now it's 6:00 UTC July 5 (= 9:00 Moscow July 5) — cal_days=1, hour=6
        now_utc = _utc(2026, 7, 5, 6, 0)

        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            expired = is_session_expired(session)

        assert expired, "Session should expire when UTC cal_days=1 and hour >= 6"

    def test_session_not_expired_just_before_utc_midnight(self):
        """At 23:58 UTC (= 02:58 Moscow), a session from the same UTC day is still active."""
        last = _utc(2026, 7, 4, 18, 0)  # 21:00 Moscow July 4
        session = _make_session(last)
        now_utc = _utc(2026, 7, 4, 23, 58)  # still UTC July 4

        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            expired = is_session_expired(session)

        assert not expired

    def test_same_day_expiry_still_works(self):
        """Sessions idle for >16h on the same UTC day are still expired."""
        last = _utc(2026, 7, 4, 2, 0)
        session = _make_session(last)
        now_utc = _utc(2026, 7, 4, 19, 0)  # 17h later, same UTC day

        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now_utc
            mock_dt.fromisoformat = datetime.fromisoformat
            expired = is_session_expired(session)

        assert expired

    def test_touch_session_stores_utc(self):
        """touch_session must store UTC time so is_session_expired comparisons are consistent."""
        session = {}
        fake_utc = _utc(2026, 7, 4, 21, 30)

        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.utcnow.return_value = fake_utc
            touch_session(session)

        assert session["last_activity_at"] == "2026-07-04T21:30:00"
