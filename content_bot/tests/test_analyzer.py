import pytest
from unittest.mock import patch, MagicMock
from content_bot.services.analyzer import analyze


@patch("content_bot.services.analyzer.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.analyzer.genai")
def test_analyze_returns_text(mock_genai):
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "Хук: Тест\nСтруктура: простая"
    mock_genai.GenerativeModel.return_value = mock_model

    result = analyze("some transcript", "tiktok", "video_short")

    assert result == "Хук: Тест\nСтруктура: простая"
    mock_genai.configure.assert_called_once_with(api_key="fake-key")


@patch("content_bot.services.analyzer.GEMINI_API_KEY", None)
def test_analyze_returns_none_when_no_api_key():
    result = analyze("transcript", "tiktok", "video_short")
    assert result is None


@patch("content_bot.services.analyzer.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.analyzer.genai")
def test_analyze_returns_none_for_empty_transcript(mock_genai):
    result = analyze("", "tiktok", "video_short")
    assert result is None
    mock_genai.GenerativeModel.assert_not_called()


@patch("content_bot.services.analyzer.GEMINI_API_KEY", "fake-key")
@patch("content_bot.services.analyzer.genai")
def test_analyze_returns_none_on_api_error(mock_genai):
    mock_genai.GenerativeModel.side_effect = Exception("API error")
    result = analyze("transcript", "tiktok", "video_short")
    assert result is None
