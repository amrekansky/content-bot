import logging
from telegram.ext import ContextTypes

from content_bot.config import TELEGRAM_CHANNEL_ID
from content_bot.services import sheets, image_card

logger = logging.getLogger(__name__)


async def publish_due_posts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """PTB JobQueue callback: post due Telegram content with image card to channel."""
    if not TELEGRAM_CHANNEL_ID:
        return

    rows = sheets.get_due_posts()
    if not rows:
        return

    logger.info("Publisher: found %d post(s) to publish", len(rows))

    for row in rows:
        try:
            card_bytes = image_card.generate_card(row.telegram_script)

            if len(row.telegram_script) <= 1024:
                await context.bot.send_photo(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    photo=card_bytes,
                    caption=row.telegram_script,
                )
            else:
                await context.bot.send_photo(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    photo=card_bytes,
                )
                await context.bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    text=row.telegram_script,
                )

            sheets.mark_published(row.row_num)
            logger.info("Publisher: posted row %d", row.row_num)
        except Exception as e:
            logger.error("Publisher: error posting row %d: %s", row.row_num, e, exc_info=True)
