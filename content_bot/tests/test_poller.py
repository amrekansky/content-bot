import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from content_bot.tasks.poller import poll_once
from content_bot.services.sheets import ApprovedRow


def _make_row(tiktok=False, telegram=True, linkedin=False, youtube=False):
    return ApprovedRow(
        row_num=2,
        content_id=42,
        url="https://tiktok.com/v/123",
        platform="tiktok",
        transcript="test transcript",
        analysis="test analysis",
        tiktok=tiktok,
        telegram=telegram,
        linkedin=linkedin,
        youtube=youtube,
    )


@pytest.mark.asyncio
@patch("content_bot.tasks.poller.sheets")
@patch("content_bot.tasks.poller.generator")
async def test_poll_once_generates_for_checked_platforms(mock_generator, mock_sheets):
    mock_sheets.get_approved_rows.return_value = [_make_row(telegram=True)]
    mock_generator.generate.return_value = "generated text"

    await poll_once(MagicMock())

    mock_sheets.update_status.assert_any_call(2, "в работе")
    mock_generator.generate.assert_called_once_with(
        "test transcript", "test analysis", "telegram"
    )
    mock_sheets.update_scripts.assert_called_once_with(2, {"telegram": "generated text"})
    mock_sheets.update_status.assert_called_with(2, "готово")


@pytest.mark.asyncio
@patch("content_bot.tasks.poller.sheets")
@patch("content_bot.tasks.poller.generator")
async def test_poll_once_skips_failed_generation(mock_generator, mock_sheets):
    mock_sheets.get_approved_rows.return_value = [_make_row(telegram=True)]
    mock_generator.generate.return_value = None

    await poll_once(MagicMock())

    mock_sheets.update_scripts.assert_called_once_with(2, {})
    mock_sheets.update_status.assert_called_with(2, "готово")


@pytest.mark.asyncio
@patch("content_bot.tasks.poller.sheets")
@patch("content_bot.tasks.poller.generator")
async def test_poll_once_does_nothing_when_no_approved_rows(mock_generator, mock_sheets):
    mock_sheets.get_approved_rows.return_value = []

    await poll_once(MagicMock())

    mock_generator.generate.assert_not_called()
    mock_sheets.update_status.assert_not_called()


@pytest.mark.asyncio
@patch("content_bot.tasks.poller.sheets")
@patch("content_bot.tasks.poller.generator")
async def test_poll_once_generates_multiple_platforms(mock_generator, mock_sheets):
    mock_sheets.get_approved_rows.return_value = [
        _make_row(tiktok=True, telegram=True)
    ]
    mock_generator.generate.return_value = "script"

    await poll_once(MagicMock())

    assert mock_generator.generate.call_count == 2
    scripts = mock_sheets.update_scripts.call_args[0][1]
    assert "tiktok" in scripts
    assert "telegram" in scripts
