import logging
from telegram.ext import Application, MessageHandler, filters

from content_bot.config import BOT_TOKEN
from content_bot.database.db import init_db
from content_bot.handlers.content_ingest import handle_message

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

    logger.info("Bot started — polling")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
