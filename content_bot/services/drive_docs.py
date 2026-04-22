import json
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

_PLATFORM_FOLDER_NAMES = {
    "telegram": "Telegram",
    "linkedin": "LinkedIn",
    "tiktok": "TikTok",
    "youtube": "YouTube",
}

_folder_id_cache: dict[str, str] = {}


def _creds() -> Credentials:
    from content_bot.config import GOOGLE_SHEETS_CREDENTIALS
    return Credentials.from_service_account_info(
        json.loads(GOOGLE_SHEETS_CREDENTIALS), scopes=_SCOPES
    )


def _drive():
    return build("drive", "v3", credentials=_creds(), cache_discovery=False)


def _docs():
    return build("docs", "v1", credentials=_creds(), cache_discovery=False)


def _get_or_create_subfolder(platform: str, root_id: str) -> str:
    if platform in _folder_id_cache:
        return _folder_id_cache[platform]

    name = _PLATFORM_FOLDER_NAMES.get(platform, platform.capitalize())
    drive = _drive()

    query = (
        f"name='{name}' and '{root_id}' in parents and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    res = drive.files().list(q=query, fields="files(id)").execute()
    files = res.get("files", [])

    if files:
        folder_id = files[0]["id"]
    else:
        folder_id = drive.files().create(
            body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [root_id]},
            fields="id",
        ).execute()["id"]

    _folder_id_cache[platform] = folder_id
    return folder_id


def create_post_doc(title: str, content: str, platform: str) -> str | None:
    """Create a Google Doc in the platform subfolder. Returns doc_id or None."""
    from content_bot.config import DRIVE_CONTENT_FOLDER_ID, GOOGLE_SHEETS_CREDENTIALS
    if not (DRIVE_CONTENT_FOLDER_ID and GOOGLE_SHEETS_CREDENTIALS):
        return None
    try:
        folder_id = _get_or_create_subfolder(platform, DRIVE_CONTENT_FOLDER_ID)
        docs = _docs()
        drive = _drive()

        doc_id = docs.documents().create(body={"title": title}).execute()["documentId"]

        drive.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents="root",
            fields="id",
        ).execute()

        if content:
            docs.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            ).execute()

        logger.info("drive_docs: created doc %s for platform=%s", doc_id, platform)
        return doc_id
    except Exception as e:
        logger.warning("drive_docs.create_post_doc failed: %s", e, exc_info=True)
        return None


def read_doc_text(doc_id: str) -> str | None:
    """Read plain text from a Google Doc."""
    from content_bot.config import GOOGLE_SHEETS_CREDENTIALS
    if not GOOGLE_SHEETS_CREDENTIALS:
        return None
    try:
        doc = _docs().documents().get(documentId=doc_id).execute()
        parts = []
        for elem in doc.get("body", {}).get("content", []):
            paragraph = elem.get("paragraph")
            if not paragraph:
                continue
            for pe in paragraph.get("elements", []):
                text_run = pe.get("textRun")
                if text_run:
                    parts.append(text_run.get("content", ""))
        return "".join(parts).strip()
    except Exception as e:
        logger.warning("drive_docs.read_doc_text failed for %s: %s", doc_id, e, exc_info=True)
        return None
