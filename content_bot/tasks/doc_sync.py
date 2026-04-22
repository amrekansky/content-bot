import logging
from telegram.ext import ContextTypes

from content_bot.services import sheets, drive_docs

logger = logging.getLogger(__name__)


async def sync_docs_to_sheets(context: ContextTypes.DEFAULT_TYPE) -> None:
    """PTB JobQueue callback: read edited Google Docs and sync changes back to Sheets."""
    rows = sheets.get_rows_for_doc_sync()
    if not rows:
        return

    for row in rows:
        for platform, doc_id in row.doc_ids.items():
            text = drive_docs.read_doc_text(doc_id)
            if not text:
                continue
            current = row.current_scripts.get(platform, "").strip()
            if text != current:
                sheets.update_script(row.row_num, platform, text)
                logger.info("doc_sync: updated %s script for row %d from Doc %s", platform, row.row_num, doc_id)
