import pytest
from unittest.mock import patch, MagicMock
from content_bot.services.sheets import ScheduledRow


def _make_row(tiktok=False, telegram=True, linkedin=False, youtube=False):
    return ScheduledRow(
        row_num=3,
        title="Как я автоматизировал контент",
        publish_date_str="2026-04-25 18:00",
        tiktok=tiktok,
        telegram=telegram,
        linkedin=linkedin,
        youtube=youtube,
    )


@pytest.mark.asyncio
@patch("content_bot.tasks.calendar_poller.sheets")
@patch("content_bot.tasks.calendar_poller.calendar_service")
async def test_poll_calendar_creates_events_for_checked_platforms(mock_cal, mock_sheets):
    from content_bot.tasks.calendar_poller import poll_calendar
    mock_sheets.get_scheduled_rows.return_value = [_make_row(telegram=True)]
    mock_cal.create_events.return_value = True

    await poll_calendar(MagicMock())

    mock_cal.create_events.assert_called_once_with(
        "Как я автоматизировал контент",
        "2026-04-25 18:00",
        ["telegram"],
    )
    mock_sheets.mark_calendared.assert_called_once_with(3)


@pytest.mark.asyncio
@patch("content_bot.tasks.calendar_poller.sheets")
@patch("content_bot.tasks.calendar_poller.calendar_service")
async def test_poll_calendar_collects_all_checked_platforms(mock_cal, mock_sheets):
    from content_bot.tasks.calendar_poller import poll_calendar
    mock_sheets.get_scheduled_rows.return_value = [_make_row(tiktok=True, telegram=True)]
    mock_cal.create_events.return_value = True

    await poll_calendar(MagicMock())

    called_platforms = mock_cal.create_events.call_args[0][2]
    assert "tiktok" in called_platforms
    assert "telegram" in called_platforms


@pytest.mark.asyncio
@patch("content_bot.tasks.calendar_poller.sheets")
@patch("content_bot.tasks.calendar_poller.calendar_service")
async def test_poll_calendar_does_nothing_when_no_rows(mock_cal, mock_sheets):
    from content_bot.tasks.calendar_poller import poll_calendar
    mock_sheets.get_scheduled_rows.return_value = []

    await poll_calendar(MagicMock())

    mock_cal.create_events.assert_not_called()
    mock_sheets.mark_calendared.assert_not_called()


@pytest.mark.asyncio
@patch("content_bot.tasks.calendar_poller.sheets")
@patch("content_bot.tasks.calendar_poller.calendar_service")
async def test_poll_calendar_skips_mark_when_events_failed(mock_cal, mock_sheets):
    from content_bot.tasks.calendar_poller import poll_calendar
    mock_sheets.get_scheduled_rows.return_value = [_make_row(telegram=True)]
    mock_cal.create_events.return_value = False

    await poll_calendar(MagicMock())

    mock_sheets.mark_calendared.assert_not_called()
