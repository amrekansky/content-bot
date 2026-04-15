import os
import pytest


def test_config_loads_required_vars(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test_token_123")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("GOOGLE_VISION_API_KEY", "vision_key_456")
    monkeypatch.setenv("LIBRARY_CHANNEL_ID", "-1001234567890")

    import importlib
    import content_bot.config as config_module
    importlib.reload(config_module)

    assert config_module.BOT_TOKEN == "test_token_123"
    assert config_module.DATABASE_URL == "postgresql://localhost/test"
    assert config_module.GOOGLE_VISION_API_KEY == "vision_key_456"
    assert config_module.LIBRARY_CHANNEL_ID == -1001234567890


def test_config_raises_on_missing_bot_token(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    monkeypatch.setenv("GOOGLE_VISION_API_KEY", "key")
    monkeypatch.setenv("LIBRARY_CHANNEL_ID", "-100123")

    import importlib
    import content_bot.config as config_module
    with pytest.raises((KeyError, ValueError)):
        importlib.reload(config_module)
