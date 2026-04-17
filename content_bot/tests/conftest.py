import os

# Set required env vars before any module-level imports in config.py fire.
# This allows tests to patch content_bot.config.* attributes directly.
os.environ.setdefault("BOT_TOKEN", "test_token")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
os.environ.setdefault("GOOGLE_VISION_API_KEY", "test_key")
os.environ.setdefault("LIBRARY_CHANNEL_ID", "-1001234567890")
