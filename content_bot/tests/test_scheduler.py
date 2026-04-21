from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

_TZ = ZoneInfo("Asia/Almaty")


@patch("content_bot.services.scheduler.POSTING_SCHEDULE", "TUE,THU,SAT@18:00")
def test_next_publish_date_finds_next_scheduled_day():
    from content_bot.services.scheduler import next_publish_date
    # Monday 2026-04-20 10:00 Almaty → next slot is Tuesday 2026-04-21 18:00
    monday = datetime(2026, 4, 20, 10, 0, tzinfo=_TZ)
    result = next_publish_date([], _now=monday)
    assert result == "2026-04-21 18:00"


@patch("content_bot.services.scheduler.POSTING_SCHEDULE", "TUE,THU,SAT@18:00")
def test_next_publish_date_skips_taken_slots():
    from content_bot.services.scheduler import next_publish_date
    # Monday 2026-04-20 → Tuesday 2026-04-21 is taken → should return Thursday 2026-04-23
    monday = datetime(2026, 4, 20, 10, 0, tzinfo=_TZ)
    result = next_publish_date(["2026-04-21 18:00"], _now=monday)
    assert result == "2026-04-23 18:00"


@patch("content_bot.services.scheduler.POSTING_SCHEDULE", "TUE,THU,SAT@18:00")
def test_next_publish_date_multiple_taken_slots():
    from content_bot.services.scheduler import next_publish_date
    # Tuesday and Thursday taken → Saturday
    monday = datetime(2026, 4, 20, 10, 0, tzinfo=_TZ)
    existing = ["2026-04-21 18:00", "2026-04-23 18:00"]
    result = next_publish_date(existing, _now=monday)
    assert result == "2026-04-25 18:00"


@patch("content_bot.services.scheduler.POSTING_SCHEDULE", None)
def test_next_publish_date_fallback_when_no_schedule():
    from content_bot.services.scheduler import next_publish_date
    monday = datetime(2026, 4, 20, 10, 0, tzinfo=_TZ)
    result = next_publish_date([], _now=monday)
    assert result == "2026-04-21 18:00"


@patch("content_bot.services.scheduler.POSTING_SCHEDULE", "invalid")
def test_next_publish_date_fallback_on_bad_schedule():
    from content_bot.services.scheduler import next_publish_date
    monday = datetime(2026, 4, 20, 10, 0, tzinfo=_TZ)
    result = next_publish_date([], _now=monday)
    assert result == "2026-04-21 18:00"
