import logging
from telegram.ext import ContextTypes

from content_bot.services import sheets, calendar_service

logger = logging.getLogger(__name__)


async def poll_calendar(context: ContextTypes.DEFAULT_TYPE) -> None:
    """PTB JobQueue callback: create Google Calendar events for ready content."""
    rows = sheets.get_scheduled_rows()
    if not rows:
        return

    logger.info("CalendarPoller: found %d row(s) to schedule", len(rows))

    for row in rows:
        try:
            platforms = [p for p, checked in [
                ("tiktok", row.tiktok),
                ("telegram", row.telegram),
                ("linkedin", row.linkedin),
                ("youtube", row.youtube),
            ] if checked]

            ok = calendar_service.create_events(row.title, row.publish_date_str, platforms)
            if ok:
                sheets.mark_calendared(row.row_num)
                logger.info("CalendarPoller: row %d scheduled for %s", row.row_num, row.publish_date_str)
            else:
                logger.warning("CalendarPoller: no events created for row %d", row.row_num)
        except Exception as e:
            logger.error("CalendarPoller: error processing row %d: %s", row.row_num, e, exc_info=True)
