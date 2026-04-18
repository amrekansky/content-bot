import logging
from telegram.ext import ContextTypes

from content_bot.services import sheets, generator

logger = logging.getLogger(__name__)


async def poll_once(context: ContextTypes.DEFAULT_TYPE) -> None:
    """PTB JobQueue callback: find approved rows, generate scripts, update Sheets."""
    rows = sheets.get_approved_rows()
    if not rows:
        return

    logger.info("Poller: found %d approved row(s)", len(rows))

    for row in rows:
        try:
            sheets.update_status(row.row_num, "в работе")

            scripts = {}
            for platform, checked in [
                ("tiktok", row.tiktok),
                ("telegram", row.telegram),
                ("linkedin", row.linkedin),
                ("youtube", row.youtube),
            ]:
                if checked:
                    text = generator.generate(row.transcript, row.analysis, platform)
                    if text:
                        scripts[platform] = text
                    else:
                        logger.warning("Generation returned None for %s row=%d",
                                       platform, row.row_num)

            sheets.update_scripts(row.row_num, scripts)
            sheets.update_status(row.row_num, "готово")
            logger.info("Poller: row %d done, platforms: %s",
                        row.row_num, list(scripts.keys()))
        except Exception as e:
            logger.error("Poller: error processing row %d: %s", row.row_num, e,
                         exc_info=True)
