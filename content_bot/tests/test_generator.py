import pytest
from unittest.mock import patch, MagicMock


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", "fake-key")
@patch("content_bot.services.generator.anthropic")
def test_generate_tiktok(mock_anthropic):
    from content_bot.services.generator import generate
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text='{"hook": "хук", "content": "TikTok скрипт текст"}')
    ]

    result = generate("some transcript", "some analysis", "tiktok")

    assert result is not None
    assert result["content"] == "TikTok скрипт текст"
    assert result["platform_label"] == "TikTok"


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", "fake-key")
@patch("content_bot.services.generator.anthropic")
def test_generate_telegram(mock_anthropic):
    from content_bot.services.generator import generate
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text='{"hook": "хук", "content": "Telegram пост текст"}')
    ]

    result = generate("transcript", "analysis", "telegram")
    assert result is not None
    assert result["content"] == "Telegram пост текст"


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", None)
def test_generate_returns_none_when_no_api_key():
    from content_bot.services.generator import generate
    result = generate("transcript", "analysis", "tiktok")
    assert result is None


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", "fake-key")
@patch("content_bot.services.generator.anthropic")
def test_generate_returns_none_on_unknown_platform(mock_anthropic):
    from content_bot.services.generator import generate
    result = generate("transcript", "analysis", "unknown_platform")
    assert result is None
    mock_anthropic.Anthropic.assert_not_called()


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", "fake-key")
@patch("content_bot.services.generator.anthropic")
def test_generate_returns_none_on_api_error(mock_anthropic):
    from content_bot.services.generator import generate
    mock_anthropic.Anthropic.side_effect = Exception("quota exceeded")
    result = generate("transcript", "analysis", "tiktok")
    assert result is None


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", "fake-key")
@patch("content_bot.services.generator.anthropic")
def test_generate_title_returns_string(mock_anthropic):
    from content_bot.services.generator import generate_title
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text="Как я сократил 4 часа работы до 10 минут с Claude")
    ]

    result = generate_title("transcript text", "analysis text")

    assert result == "Как я сократил 4 часа работы до 10 минут с Claude"
    mock_client.messages.create.assert_called_once()


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", None)
def test_generate_title_returns_none_when_no_api_key():
    from content_bot.services.generator import generate_title
    assert generate_title("transcript", "analysis") is None


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", "fake-key")
@patch("content_bot.services.generator.anthropic")
def test_generate_title_strips_quotes(mock_anthropic):
    from content_bot.services.generator import generate_title
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value.content = [
        MagicMock(text='"Заголовок в кавычках"')
    ]

    result = generate_title("t", "a")
    assert result == "Заголовок в кавычках"


@patch("content_bot.services.generator.ANTHROPIC_API_KEY", "fake-key")
@patch("content_bot.services.generator.anthropic")
def test_generate_title_returns_none_on_api_error(mock_anthropic):
    from content_bot.services.generator import generate_title
    mock_anthropic.Anthropic.side_effect = Exception("API error")
    assert generate_title("t", "a") is None
