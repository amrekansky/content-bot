import logging
from telegram.ext import ContextTypes

from content_bot.services import sheets, generator

logger = logging.getLogger(__name__)


async def poll_once(context: ContextTypes.DEFAULT_TYPE) -> None:
    """PTB JobQueue callback: find approved rows, generate scripts, write to Content Calendar."""
    rows = sheets.get_approved_rows()
    if not rows:
        return

    logger.info("Poller: found %d approved row(s)", len(rows))

    for row in rows:
        try:
            sheets.update_status(row.row_num, "в работе")

            generated_any = False
            for platform, checked in [
                ("tiktok", row.tiktok),
                ("telegram", row.telegram),
                ("linkedin", row.linkedin),
                ("youtube", row.youtube),
            ]:
                if not checked:
                    continue
                result = generator.generate(row.transcript, row.analysis, platform)
                if not result:
                    logger.warning("Generation returned None for %s row=%d", platform, row.row_num)
                    continue
                sheets.append_to_calendar(
                    platform_label=result["platform_label"],
                    format_label=result["format_label"],
                    hook=result["hook"],
                    content=result["content"],
                    source_url=row.url,
                )
                generated_any = True

            sheets.update_status(row.row_num, "готово" if generated_any else "ошибка")
            logger.info("Poller: row %d done", row.row_num)
        except Exception as e:
            logger.error("Poller: error processing row %d: %s", row.row_num, e, exc_info=True)
            sheets.update_status(row.row_num, "одобрено")
