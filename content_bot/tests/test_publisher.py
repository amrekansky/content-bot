import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from content_bot.services.sheets import DuePost


def _make_post(script="Текст поста для Telegram канала"):
    return DuePost(row_num=3, title="Заголовок", telegram_script=script)


@pytest.mark.asyncio
@patch("content_bot.tasks.publisher.TELEGRAM_CHANNEL_ID", "@headlessaimode")
@patch("content_bot.tasks.publisher.sheets")
@patch("content_bot.tasks.publisher.image_card")
async def test_publish_sends_photo_with_caption_when_short(mock_image_card, mock_sheets):
    from content_bot.tasks.publisher import publish_due_posts
    mock_sheets.get_due_posts.return_value = [_make_post("Короткий пост")]
    mock_image_card.generate_card.return_value = b"fake_png_bytes"

    context = MagicMock()
    context.bot.send_photo = AsyncMock()
    context.bot.send_message = AsyncMock()

    await publish_due_posts(context)

    context.bot.send_photo.assert_called_once_with(
        chat_id="@headlessaimode",
        photo=b"fake_png_bytes",
        caption="Короткий пост",
    )
    context.bot.send_message.assert_not_called()
    mock_sheets.mark_published.assert_called_once_with(3)


@pytest.mark.asyncio
@patch("content_bot.tasks.publisher.TELEGRAM_CHANNEL_ID", "@headlessaimode")
@patch("content_bot.tasks.publisher.sheets")
@patch("content_bot.tasks.publisher.image_card")
async def test_publish_sends_photo_then_text_when_long(mock_image_card, mock_sheets):
    from content_bot.tasks.publisher import publish_due_posts
    long_script = "А" * 1025
    mock_sheets.get_due_posts.return_value = [_make_post(long_script)]
    mock_image_card.generate_card.return_value = b"fake_png_bytes"

    context = MagicMock()
    context.bot.send_photo = AsyncMock()
    context.bot.send_message = AsyncMock()

    await publish_due_posts(context)

    context.bot.send_photo.assert_called_once_with(
        chat_id="@headlessaimode",
        photo=b"fake_png_bytes",
    )
    context.bot.send_message.assert_called_once_with(
        chat_id="@headlessaimode",
        text=long_script,
    )
    mock_sheets.mark_published.assert_called_once_with(3)


@pytest.mark.asyncio
@patch("content_bot.tasks.publisher.TELEGRAM_CHANNEL_ID", "@headlessaimode")
@patch("content_bot.tasks.publisher.sheets")
@patch("content_bot.tasks.publisher.image_card")
async def test_publish_does_nothing_when_no_due_posts(mock_image_card, mock_sheets):
    from content_bot.tasks.publisher import publish_due_posts
    mock_sheets.get_due_posts.return_value = []

    context = MagicMock()
    context.bot.send_photo = AsyncMock()

    await publish_due_posts(context)

    context.bot.send_photo.assert_not_called()
    mock_sheets.mark_published.assert_not_called()


@pytest.mark.asyncio
@patch("content_bot.tasks.publisher.TELEGRAM_CHANNEL_ID", None)
@patch("content_bot.tasks.publisher.sheets")
@patch("content_bot.tasks.publisher.image_card")
async def test_publish_does_nothing_when_no_channel_id(mock_image_card, mock_sheets):
    from content_bot.tasks.publisher import publish_due_posts

    context = MagicMock()
    context.bot.send_photo = AsyncMock()

    await publish_due_posts(context)

    mock_sheets.get_due_posts.assert_not_called()
    context.bot.send_photo.assert_not_called()
