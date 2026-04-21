import json
import logging
from dataclasses import dataclass
from datetime import datetime

import gspread

from content_bot.config import (
    GOOGLE_SHEETS_ID,
    CONTENT_CALENDAR_SHEETS_ID,
    GOOGLE_SHEETS_CREDENTIALS,
)

logger = logging.getLogger(__name__)

HEADERS = [
    "ID", "URL", "Платформа", "Название", "Дата",
    "Транскрипт", "Анализ", "Статус",
    "TikTok ✓", "Telegram ✓", "LinkedIn ✓", "YouTube ✓",
    "TikTok скрипт", "Telegram пост", "LinkedIn пост", "YouTube скрипт",
    "Дата публикации", "В календаре ✓",
]

# Column numbers (1-based, matches gspread update_cell)
_COL_STATUS = 8
_COL_TIKTOK_CHECK = 9
_COL_TELEGRAM_CHECK = 10
_COL_LINKEDIN_CHECK = 11
_COL_YOUTUBE_CHECK = 12
_COL_TIKTOK_SCRIPT = 13
_COL_TELEGRAM_POST = 14
_COL_LINKEDIN_POST = 15
_COL_YOUTUBE_SCRIPT = 16
_COL_PUBLISH_DATE = 17
_COL_CALENDARED = 18


@dataclass
class ApprovedRow:
    row_num: int
    content_id: int
    url: str
    platform: str
    transcript: str
    analysis: str
    tiktok: bool
    telegram: bool
    linkedin: bool
    youtube: bool


@dataclass
class ScheduledRow:
    row_num: int
    title: str
    publish_date_str: str
    tiktok: bool
    telegram: bool
    linkedin: bool
    youtube: bool


def _get_sheet():
    creds = json.loads(GOOGLE_SHEETS_CREDENTIALS)
    client = gspread.service_account_from_dict(creds)
    return client.open_by_key(GOOGLE_SHEETS_ID).sheet1


def append_row(
    content_id: int,
    url: str,
    platform: str,
    title: str | None,
    transcript: str | None,
    analysis: str | None,
) -> None:
    """Append a new content row to Google Sheets. Silently skips if credentials missing."""
    if not (GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS):
        logger.warning("Sheets append_row skipped: credentials not configured")
        return
    try:
        sheet = _get_sheet()
        # Find next empty row: scan col A for last non-empty value
        col_a = sheet.col_values(1)
        last_data_row = 0
        for i, val in enumerate(col_a):
            if val and val.strip():
                last_data_row = i + 1
        if last_data_row == 0:
            sheet.update("A1", [HEADERS])
            last_data_row = 1
        next_row = last_data_row + 1
        row_data = [
            content_id,
            url,
            platform,
            title or "",
            datetime.now().strftime("%Y-%m-%d"),
            transcript or "",
            analysis or "",
            "новый",
            False, False, False, False,
            "", "", "", "",
        ]
        sheet.update(f"A{next_row}", [row_data])
        logger.info("Sheets: appended row for content_id=%d at row %d", content_id, next_row)
    except Exception as e:
        logger.warning("Sheets append_row failed: %s", e, exc_info=True)


def get_approved_rows() -> list[ApprovedRow]:
    """Return rows where Статус='одобрено' and at least one platform checkbox is True."""
    if not (GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS):
        return []
    try:
        sheet = _get_sheet()
        all_rows = sheet.get_all_values()
        approved = []
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) < 12:
                continue
            if row[_COL_STATUS - 1] != "одобрено":
                continue
            tiktok = str(row[_COL_TIKTOK_CHECK - 1]).upper() == "TRUE"
            telegram = str(row[_COL_TELEGRAM_CHECK - 1]).upper() == "TRUE"
            linkedin = str(row[_COL_LINKEDIN_CHECK - 1]).upper() == "TRUE"
            youtube = str(row[_COL_YOUTUBE_CHECK - 1]).upper() == "TRUE"
            if not any([tiktok, telegram, linkedin, youtube]):
                continue
            try:
                content_id = int(row[0])
            except (ValueError, IndexError):
                continue
            approved.append(ApprovedRow(
                row_num=i,
                content_id=content_id,
                url=row[1],
                platform=row[2],
                transcript=row[5],
                analysis=row[6],
                tiktok=tiktok,
                telegram=telegram,
                linkedin=linkedin,
                youtube=youtube,
            ))
        return approved
    except Exception as e:
        logger.warning("Sheets get_approved_rows failed: %s", e, exc_info=True)
        return []


def update_status(row_num: int, status: str) -> None:
    """Update the Статус cell for a given row."""
    if not (GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS):
        return
    try:
        sheet = _get_sheet()
        sheet.update_cell(row_num, _COL_STATUS, status)
    except Exception as e:
        logger.warning("Sheets update_status failed: %s", e, exc_info=True)


def get_scheduled_rows() -> list[ScheduledRow]:
    """Return rows where status='готово', publish date set, not yet calendared."""
    if not (GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS):
        return []
    try:
        sheet = _get_sheet()
        all_rows = sheet.get_all_values()
        result = []
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) < 8:
                continue
            if row[_COL_STATUS - 1] != "готово":
                continue
            publish_date = row[_COL_PUBLISH_DATE - 1] if len(row) >= 17 else ""
            if not publish_date or not publish_date.strip():
                continue
            calendared = row[_COL_CALENDARED - 1].upper() if len(row) >= 18 else ""
            if calendared == "TRUE":
                continue
            tiktok = str(row[_COL_TIKTOK_CHECK - 1]).upper() == "TRUE"
            telegram = str(row[_COL_TELEGRAM_CHECK - 1]).upper() == "TRUE"
            linkedin = str(row[_COL_LINKEDIN_CHECK - 1]).upper() == "TRUE"
            youtube = str(row[_COL_YOUTUBE_CHECK - 1]).upper() == "TRUE"
            title = row[3] if len(row) >= 4 else ""
            result.append(ScheduledRow(
                row_num=i,
                title=title,
                publish_date_str=publish_date.strip(),
                tiktok=tiktok,
                telegram=telegram,
                linkedin=linkedin,
                youtube=youtube,
            ))
        return result
    except Exception as e:
        logger.warning("Sheets get_scheduled_rows failed: %s", e, exc_info=True)
        return []


def update_scripts(row_num: int, scripts: dict[str, str]) -> None:
    """Write generated scripts into platform columns for a given row."""
    if not (GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS):
        return
    try:
        sheet = _get_sheet()
        col_map = {
            "tiktok": _COL_TIKTOK_SCRIPT,
            "telegram": _COL_TELEGRAM_POST,
            "linkedin": _COL_LINKEDIN_POST,
            "youtube": _COL_YOUTUBE_SCRIPT,
        }
        for platform, text in scripts.items():
            if platform in col_map:
                sheet.update_cell(row_num, col_map[platform], text)
    except Exception as e:
        logger.warning("Sheets update_scripts failed: %s", e, exc_info=True)


def mark_calendared(row_num: int) -> None:
    """Set 'В календаре ✓' = TRUE and status = 'запланировано'."""
    if not (GOOGLE_SHEETS_ID and GOOGLE_SHEETS_CREDENTIALS):
        return
    try:
        sheet = _get_sheet()
        sheet.update_cell(row_num, _COL_CALENDARED, True)
        sheet.update_cell(row_num, _COL_STATUS, "запланировано")
    except Exception as e:
        logger.warning("Sheets mark_calendared failed: %s", e, exc_info=True)


# ── Content Calendar ───────────────────────────────────────────────────────────

_CALENDAR_HEADERS = ["Дата", "Платформа", "Формат", "Хук", "Контент", "Статус", "Источник URL", "Файл"]


def _get_calendar_sheet():
    creds = json.loads(GOOGLE_SHEETS_CREDENTIALS)
    client = gspread.service_account_from_dict(creds)
    return client.open_by_key(CONTENT_CALENDAR_SHEETS_ID).sheet1


def append_to_calendar(
    platform_label: str,
    format_label: str,
    hook: str,
    content: str,
    source_url: str,
) -> None:
    """Append a generated post to the Content Calendar sheet."""
    if not GOOGLE_SHEETS_CREDENTIALS:
        logger.warning("Calendar append skipped: credentials not configured")
        return
    try:
        sheet = _get_calendar_sheet()
        col_a = sheet.col_values(1)
        last_row = sum(1 for v in col_a if v and v.strip())
        if last_row == 0:
            sheet.update("A1", [_CALENDAR_HEADERS])
            last_row = 1
        next_row = last_row + 1
        row_data = [
            datetime.now().strftime("%Y-%m-%d"),
            platform_label,
            format_label,
            hook,
            content,
            "черновик",
            source_url,
            "",
        ]
        sheet.update(f"A{next_row}", [row_data])
        logger.info("Calendar: appended %s row at %d", platform_label, next_row)
    except Exception as e:
        logger.warning("Calendar append failed: %s", e, exc_info=True)
