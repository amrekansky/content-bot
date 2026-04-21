import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required env var {key!r} is not set")
    return val


def _require_int(key: str) -> int:
    val = _require(key)
    try:
        return int(val)
    except ValueError:
        raise ValueError(f"Env var {key!r} must be an integer, got {val!r}")


BOT_TOKEN: str = _require("BOT_TOKEN")
DATABASE_URL: str = _require("DATABASE_URL")
GOOGLE_VISION_API_KEY: str = _require("GOOGLE_VISION_API_KEY")
LIBRARY_CHANNEL_ID: int = _require_int("LIBRARY_CHANNEL_ID")
GROQ_API_KEY: str | None = os.environ.get("GROQ_API_KEY")
WEBSHARE_PROXY_URL: str | None = os.environ.get("WEBSHARE_PROXY_URL")
INSTAGRAM_COOKIES_B64: str | None = os.environ.get("INSTAGRAM_COOKIES_B64")
YOUTUBE_COOKIES_B64: str | None = os.environ.get("YOUTUBE_COOKIES_B64")
INSTAGRAM_USERNAME: str | None = os.environ.get("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD: str | None = os.environ.get("INSTAGRAM_PASSWORD")
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")
GOOGLE_SHEETS_ID: str | None = os.environ.get("GOOGLE_SHEETS_ID")
CONTENT_CALENDAR_SHEETS_ID: str = os.environ.get(
    "CONTENT_CALENDAR_SHEETS_ID", "1Q7sAPrh7f0XbCls9zatz9_7GjgHiaKNbz1SzLGuL1NI"
)
GOOGLE_SHEETS_CREDENTIALS: str | None = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_CALENDAR_ID: str | None = os.environ.get("GOOGLE_CALENDAR_ID")
