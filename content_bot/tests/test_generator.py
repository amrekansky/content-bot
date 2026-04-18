import pytest
from unittest.mock import patch, MagicMock
from content_bot.services.generator import generate


@patch("content_bot.services.generator.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.generator.genai")
def test_generate_tiktok(mock_genai):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "TikTok скрипт текст"
    mock_genai.GenerativeModel.return_value = mock_model

    result = generate("some transcript", "some analysis", "tiktok")

    assert result == "TikTok скрипт текст"
    mock_genai.configure.assert_called_once_with(api_key="fake-key")


@patch("content_bot.services.generator.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.generator.genai")
def test_generate_telegram(mock_genai):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "Telegram пост текст"
    mock_genai.GenerativeModel.return_value = mock_model

    result = generate("transcript", "analysis", "telegram")
    assert result == "Telegram пост текст"


@patch("content_bot.services.generator.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.generator.genai")
def test_generate_linkedin(mock_genai):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "LinkedIn пост"
    mock_genai.GenerativeModel.return_value = mock_model

    result = generate("transcript", "analysis", "linkedin")
    assert result == "LinkedIn пост"


@patch("content_bot.services.generator.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.generator.genai")
def test_generate_youtube(mock_genai):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "YouTube скрипт"
    mock_genai.GenerativeModel.return_value = mock_model

    result = generate("transcript", "analysis", "youtube")
    assert result == "YouTube скрипт"


@patch("content_bot.services.generator.GEMINI_API_KEY", None)
def test_generate_returns_none_when_no_api_key():
    result = generate("transcript", "analysis", "tiktok")
    assert result is None


@patch("content_bot.services.generator.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.generator.genai")
def test_generate_returns_none_on_unknown_platform(mock_genai):
    result = generate("transcript", "analysis", "unknown_platform")
    assert result is None
    mock_genai.GenerativeModel.assert_not_called()


@patch("content_bot.services.generator.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.generator.genai")
def test_generate_returns_none_on_api_error(mock_genai):
    mock_genai.GenerativeModel.side_effect = Exception("quota exceeded")
    result = generate("transcript", "analysis", "tiktok")
    assert result is None
