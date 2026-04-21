import json
import logging
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

from content_bot.config import GOOGLE_CALENDAR_ID, GOOGLE_SHEETS_CREDENTIALS

logger = logging.getLogger(__name__)

_TIMEZONE = "Asia/Almaty"
_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_DATE_FORMATS = ["%Y-%m-%d %H:%M", "%Y-%m-%d"]

_PLATFORM_NAMES = {
    "tiktok": "TikTok",
    "telegram": "Telegram",
    "linkedin": "LinkedIn",
    "youtube": "YouTube",
    "threads": "Threads",
}


def _parse_date(date_str: str) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _get_service():
    creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=_SCOPES
    )
    return build("calendar", "v3", credentials=creds)


def create_events(title: str, publish_date_str: str, platforms: list[str]) -> bool:
    """Create one Google Calendar event per platform. Returns True if any event created."""
    if not (GOOGLE_CALENDAR_ID and GOOGLE_SHEETS_CREDENTIALS):
        logger.warning("Calendar events skipped: GOOGLE_CALENDAR_ID not configured")
        return False

    publish_dt = _parse_date(publish_date_str)
    if publish_dt is None:
        logger.warning("Cannot parse publish date: %r", publish_date_str)
        return False

    start_iso = publish_dt.isoformat()
    end_iso = (publish_dt + timedelta(hours=1)).isoformat()

    try:
        service = _get_service()
        created = 0
        for platform in platforms:
            platform_name = _PLATFORM_NAMES.get(platform, platform.capitalize())
            event_title = f"{platform_name} — {title}"
            body = {
                "summary": event_title,
                "start": {"dateTime": start_iso, "timeZone": _TIMEZONE},
                "end": {"dateTime": end_iso, "timeZone": _TIMEZONE},
                "reminders": {"useDefault": True},
            }
            service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=body).execute()
            logger.info("Calendar: created event %r", event_title)
            created += 1
        return created > 0
    except Exception as e:
        logger.warning("Calendar create_events failed: %s", e, exc_info=True)
        return False
