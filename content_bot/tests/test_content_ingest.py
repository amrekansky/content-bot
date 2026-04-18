import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, Chat
from content_bot.handlers.content_ingest import handle_message


def make_update(text=None, photo=None, document=None):
    update = MagicMock()
    update.message.text = text
    update.message.photo = photo
    update.message.document = document
    update.message.reply_text = AsyncMock()
    update.message.bot = AsyncMock()
    update.message.bot.get_file = AsyncMock()
    return update


def make_context():
    ctx = MagicMock()
    ctx.bot = AsyncMock()
    ctx.bot.send_message = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_handle_url_message_success():
    update = make_update(text="https://www.youtube.com/watch?v=abc123")
    ctx = make_context()

    mock_result = MagicMock()
    mock_result.platform = "youtube"
    mock_result.content_type = "video"
    mock_result.transcript = "Тестовый транскрипт видео"
    mock_result.source_url = "https://www.youtube.com/watch?v=abc123"

    with patch("content_bot.handlers.content_ingest.process_url", return_value=mock_result), \
         patch("content_bot.handlers.content_ingest.insert_content", return_value=42), \
         patch("content_bot.handlers.content_ingest.init_db"), \
         patch("content_bot.handlers.content_ingest.LIBRARY_CHANNEL_ID", -1001234567890):

        await handle_message(update, ctx)

    # Verify initial "processing" reply
    first_reply = update.message.reply_text.call_args_list[0][0][0]
    assert "⏳" in first_reply

    # Verify success reply contains the record ID
    second_reply = update.message.reply_text.call_args_list[1][0][0]
    assert "42" in second_reply
    assert "✅" in second_reply

    # Verify archive card sent to channel
    ctx.bot.send_message.assert_called_once()
    channel_id = ctx.bot.send_message.call_args[1]["chat_id"]
    assert channel_id == -1001234567890


@pytest.mark.asyncio
async def test_handle_unknown_url_replies_unsupported():
    update = make_update(text="https://example.com/not-supported")
    ctx = make_context()

    with patch("content_bot.handlers.content_ingest.process_url", return_value=None), \
         patch("content_bot.handlers.content_ingest.init_db"):

        await handle_message(update, ctx)

    # Should have replied with unsupported message
    assert update.message.reply_text.call_count >= 1
    # Find the error reply (may be after the "processing" reply)
    all_replies = [c[0][0] for c in update.message.reply_text.call_args_list]
    error_reply = all_replies[-1]
    assert "❌" in error_reply or "не поддерживается" in error_reply.lower()

    # Must NOT send to archive channel
    ctx.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_non_url_text_is_ignored():
    update = make_update(text="привет")
    ctx = make_context()

    with patch("content_bot.handlers.content_ingest.process_url") as mock_proc, \
         patch("content_bot.handlers.content_ingest.init_db"):

        await handle_message(update, ctx)

    mock_proc.assert_not_called()
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_handle_url_no_transcript():
    """URL processed but no subtitles found — should still save and reply."""
    update = make_update(text="https://www.tiktok.com/@user/video/123")
    ctx = make_context()

    mock_result = MagicMock()
    mock_result.platform = "tiktok"
    mock_result.content_type = "video_short"
    mock_result.transcript = None
    mock_result.source_url = "https://www.tiktok.com/@user/video/123"

    with patch("content_bot.handlers.content_ingest.process_url", return_value=mock_result), \
         patch("content_bot.handlers.content_ingest.insert_content", return_value=7), \
         patch("content_bot.handlers.content_ingest.init_db"), \
         patch("content_bot.handlers.content_ingest.LIBRARY_CHANNEL_ID", -1001234567890):

        await handle_message(update, ctx)

    # Still saves and sends archive card even without transcript
    ctx.bot.send_message.assert_called_once()
    success_reply = update.message.reply_text.call_args_list[-1][0][0]
    assert "7" in success_reply


def _make_update(text="https://www.youtube.com/watch?v=abc123"):
    user = MagicMock(spec=User)
    chat = MagicMock(spec=Chat)
    message = MagicMock(spec=Message)
    message.text = text
    message.photo = None
    message.document = None
    message.reply_text = AsyncMock()
    message.chat = chat
    update = MagicMock(spec=Update)
    update.message = message
    return update


@pytest.mark.asyncio
@patch("content_bot.handlers.content_ingest.process_url")
@patch("content_bot.handlers.content_ingest.insert_content", return_value=7)
@patch("content_bot.handlers.content_ingest.analyzer")
@patch("content_bot.handlers.content_ingest.sheets")
@patch("content_bot.handlers.content_ingest.init_db")
@patch("content_bot.handlers.content_ingest.LIBRARY_CHANNEL_ID", -1001234567890)
async def test_url_triggers_analysis_and_sheets(
    mock_init_db, mock_sheets, mock_analyzer, mock_insert, mock_process
):
    mock_process.return_value = MagicMock(
        source_url="https://www.youtube.com/watch?v=abc123",
        platform="youtube",
        content_type="video",
        transcript="transcript text",
        title="Test Video Title",
    )
    mock_analyzer.analyze.return_value = "Хук: тест"

    context = MagicMock()
    context.bot.send_message = AsyncMock()
    update = _make_update("https://www.youtube.com/watch?v=abc123")

    await handle_message(update, context)

    mock_analyzer.analyze.assert_called_once_with(
        "transcript text", "youtube", "video"
    )
    mock_sheets.append_row.assert_called_once_with(
        7,
        "https://www.youtube.com/watch?v=abc123",
        "youtube",
        "Test Video Title",
        "transcript text",
        "Хук: тест",
    )
