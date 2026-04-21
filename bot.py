import logging
from telegram.ext import Application, MessageHandler, filters

from content_bot.config import BOT_TOKEN
from content_bot.database.db import init_db
from content_bot.handlers.content_ingest import handle_message
from content_bot.tasks.poller import poll_once
from content_bot.tasks.calendar_poller import poll_calendar
from content_bot.tasks.publisher import publish_due_posts

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

    # Module 2: generate scripts from approved Library rows
    app.job_queue.run_repeating(poll_once, interval=300, first=60)
    logger.info("Poller scheduled: every 300s, first run in 60s")

    # Module 3: create Google Calendar events for ready content
    app.job_queue.run_repeating(poll_calendar, interval=300, first=90)
    logger.info("CalendarPoller scheduled: every 300s, first run in 90s")

    # Module 4: publish due Telegram posts with image card
    app.job_queue.run_repeating(publish_due_posts, interval=60, first=30)
    logger.info("Publisher scheduled: every 60s, first run in 30s")

    logger.info("Bot started — polling")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
