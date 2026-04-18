import pytest
from unittest.mock import patch, MagicMock
from content_bot.services.sheets import (
    append_row,
    get_approved_rows,
    update_status,
    update_scripts,
    ApprovedRow,
)


def _make_sheet_mock(rows=None):
    sheet = MagicMock()
    sheet.get_all_values.return_value = rows or []
    return sheet


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_append_row_adds_row(mock_get_sheet):
    sheet = _make_sheet_mock(rows=[["ID", "URL"]])
    mock_get_sheet.return_value = sheet

    append_row(1, "https://tiktok.com/v/123", "tiktok", "Test video",
               "transcript text", "analysis text")

    sheet.append_row.assert_called_once()
    call_args = sheet.append_row.call_args[0][0]
    assert call_args[0] == 1          # ID
    assert call_args[1] == "https://tiktok.com/v/123"
    assert call_args[7] == "новый"    # Статус


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_append_row_skipped_when_no_credentials(mock_get_sheet):
    with patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", None):
        append_row(1, "https://tiktok.com/v/123", "tiktok", "Test", "t", "a")
    mock_get_sheet.assert_not_called()


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_approved_rows_returns_approved(mock_get_sheet):
    header = ["ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
              "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
              "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт"]
    row = ["42", "https://t.com", "tiktok", "title", "2026-04-18",
           "transcript", "analysis", "одобрено",
           "TRUE", "FALSE", "FALSE", "FALSE",
           "", "", "", ""]
    sheet = _make_sheet_mock(rows=[header, row])
    mock_get_sheet.return_value = sheet

    result = get_approved_rows()

    assert len(result) == 1
    assert result[0].content_id == 42
    assert result[0].tiktok is True
    assert result[0].telegram is False
    assert result[0].row_num == 2


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_approved_rows_skips_non_approved(mock_get_sheet):
    header = ["ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
              "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
              "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт"]
    row = ["42", "https://t.com", "tiktok", "title", "2026-04-18",
           "transcript", "analysis", "новый",
           "TRUE", "FALSE", "FALSE", "FALSE",
           "", "", "", ""]
    sheet = _make_sheet_mock(rows=[header, row])
    mock_get_sheet.return_value = sheet

    result = get_approved_rows()
    assert result == []


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_update_status_calls_update_cell(mock_get_sheet):
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    update_status(3, "в работе")

    sheet.update_cell.assert_called_once_with(3, 8, "в работе")


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_update_scripts_writes_tiktok_and_telegram(mock_get_sheet):
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    update_scripts(3, {"tiktok": "tiktok text", "telegram": "telegram text"})

    calls = [c[0] for c in sheet.update_cell.call_args_list]
    assert (3, 13, "tiktok text") in calls
    assert (3, 14, "telegram text") in calls
