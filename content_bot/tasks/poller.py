import logging
from datetime import datetime
from telegram.ext import ContextTypes

from content_bot.services import sheets, generator, scheduler, drive_docs

logger = logging.getLogger(__name__)


async def poll_once(context: ContextTypes.DEFAULT_TYPE) -> None:
    """PTB JobQueue callback: generate scripts + title + assign date for approved rows."""
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
                if not checked:
                    continue
                result = generator.generate(row.transcript, row.analysis, platform)
                if not result:
                    logger.warning("Generation returned None for %s row=%d", platform, row.row_num)
                    continue
                scripts[platform] = result["content"]

            if scripts:
                sheets.update_scripts(row.row_num, scripts)

                title = generator.generate_title(row.transcript, row.analysis)
                if title:
                    sheets.update_title(row.row_num, title)

                existing_dates = sheets.get_all_publish_dates()
                pub_date = scheduler.next_publish_date(existing_dates)
                sheets.assign_date(row.row_num, pub_date)

                doc_title = f"{title or row.url} — {datetime.now().strftime('%Y-%m-%d')}"
                doc_ids = {}
                for platform, content in scripts.items():
                    doc_id = drive_docs.create_post_doc(
                        title=f"{platform.capitalize()} — {doc_title}",
                        content=content,
                        platform=platform,
                    )
                    if doc_id:
                        doc_ids[platform] = doc_id
                if doc_ids:
                    sheets.update_doc_ids(row.row_num, doc_ids)

            sheets.update_status(row.row_num, "готово" if scripts else "ошибка")
            logger.info("Poller: row %d done, platforms: %s", row.row_num, list(scripts.keys()))
        except Exception as e:
            logger.error("Poller: error processing row %d: %s", row.row_num, e, exc_info=True)
            sheets.update_status(row.row_num, "одобрено")
