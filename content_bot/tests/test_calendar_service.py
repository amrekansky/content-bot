import pytest
from unittest.mock import patch, MagicMock
from content_bot.services.calendar_service import create_events


@patch("content_bot.services.calendar_service.GOOGLE_CALENDAR_ID", "test@gmail.com")
@patch("content_bot.services.calendar_service.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.calendar_service._get_service")
def test_create_events_inserts_one_per_platform(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    result = create_events("Мой заголовок", "2026-04-25 18:00", ["telegram", "tiktok"])

    assert result is True
    assert mock_service.events().insert.call_count == 2

    calls = mock_service.events().insert.call_args_list
    summaries = [c.kwargs["body"]["summary"] for c in calls]
    assert "Telegram — Мой заголовок" in summaries
    assert "TikTok — Мой заголовок" in summaries


@patch("content_bot.services.calendar_service.GOOGLE_CALENDAR_ID", "test@gmail.com")
@patch("content_bot.services.calendar_service.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.calendar_service._get_service")
def test_create_events_uses_correct_calendar_id(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    create_events("Заголовок", "2026-04-25 18:00", ["telegram"])

    call_kwargs = mock_service.events().insert.call_args.kwargs
    assert call_kwargs["calendarId"] == "test@gmail.com"


@patch("content_bot.services.calendar_service.GOOGLE_CALENDAR_ID", "test@gmail.com")
@patch("content_bot.services.calendar_service.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.calendar_service._get_service")
def test_create_events_accepts_date_without_time(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    result = create_events("Заголовок", "2026-04-25", ["telegram"])

    assert result is True
    mock_service.events().insert.assert_called_once()


@patch("content_bot.services.calendar_service.GOOGLE_CALENDAR_ID", None)
def test_create_events_returns_false_when_no_calendar_id():
    result = create_events("Заголовок", "2026-04-25 18:00", ["telegram"])
    assert result is False


@patch("content_bot.services.calendar_service.GOOGLE_CALENDAR_ID", "test@gmail.com")
@patch("content_bot.services.calendar_service.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.calendar_service._get_service")
def test_create_events_returns_false_on_unparseable_date(mock_get_service):
    result = create_events("Заголовок", "не дата", ["telegram"])
    assert result is False
    mock_get_service.assert_not_called()


@patch("content_bot.services.calendar_service.GOOGLE_CALENDAR_ID", "test@gmail.com")
@patch("content_bot.services.calendar_service.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.calendar_service._get_service")
def test_create_events_returns_false_on_api_error(mock_get_service):
    mock_get_service.side_effect = Exception("API error")
    result = create_events("Заголовок", "2026-04-25 18:00", ["telegram"])
    assert result is False
