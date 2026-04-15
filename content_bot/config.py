import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required env var {key!r} is not set")
    return val


BOT_TOKEN: str = _require("BOT_TOKEN")
DATABASE_URL: str = _require("DATABASE_URL")
GOOGLE_VISION_API_KEY: str = _require("GOOGLE_VISION_API_KEY")
LIBRARY_CHANNEL_ID: int = int(_require("LIBRARY_CHANNEL_ID"))
