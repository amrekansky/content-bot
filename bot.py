import logging
from telegram.ext import Application, MessageHandler, filters

from content_bot.config import BOT_TOKEN
from content_bot.database.db import init_db
from content_bot.handlers.content_ingest import handle_message
from content_bot.tasks.poller import poll_once

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    init_db()
    logger.info("DB initialized")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    # Module 2: poll Google Sheets every 5 minutes
    app.job_queue.run_repeating(poll_once, interval=300, first=60)
    logger.info("Poller scheduled: every 300s, first run in 60s")

    logger.info("Bot started — polling")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
