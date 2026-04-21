import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from content_bot.config import POSTING_SCHEDULE

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Almaty")
_DAY_MAP = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


def _parse_schedule() -> list[tuple[int, int, int]]:
    if not POSTING_SCHEDULE:
        return []
    try:
        days_str, time_str = POSTING_SCHEDULE.split("@")
        hour, minute = map(int, time_str.split(":"))
        days = [d.strip().upper() for d in days_str.split(",")]
        return [(_DAY_MAP[d], hour, minute) for d in days if d in _DAY_MAP]
    except Exception as e:
        logger.warning("Cannot parse POSTING_SCHEDULE %r: %s", POSTING_SCHEDULE, e)
        return []


def next_publish_date(existing_dates: list[str], _now: datetime | None = None) -> str:
    """Find next available posting slot not already in existing_dates.

    Args:
        existing_dates: list of 'YYYY-MM-DD HH:MM' strings already assigned.
        _now: override current time (for testing).

    Returns:
        Date string in 'YYYY-MM-DD HH:MM' format (Almaty timezone).
        Falls back to tomorrow 18:00 if POSTING_SCHEDULE not set or invalid.
    """
    schedule = _parse_schedule()
    now = _now or datetime.now(_TZ)
    existing = {d.strip() for d in existing_dates if d.strip()}

    fallback = (now + timedelta(days=1)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )

    if not schedule:
        return fallback.strftime("%Y-%m-%d %H:%M")

    for days_ahead in range(1, 62):
        candidate = now + timedelta(days=days_ahead)
        weekday = candidate.weekday()
        for sched_weekday, hour, minute in schedule:
            if sched_weekday == weekday:
                slot = candidate.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                slot_str = slot.strftime("%Y-%m-%d %H:%M")
                if slot_str not in existing:
                    return slot_str

    return fallback.strftime("%Y-%m-%d %H:%M")
