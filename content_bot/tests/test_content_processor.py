import pytest
from unittest.mock import patch, MagicMock, mock_open
from content_bot.services.content_processor import (
    detect_url_type,
    parse_vtt_text,
    process_url,
    ProcessedContent,
    _extract_carousel_text,
)


# --- detect_url_type ---

def test_detects_tiktok():
    result = detect_url_type("https://www.tiktok.com/@user/video/123")
    assert result["platform"] == "tiktok"
    assert result["content_type"] == "video_short"


def test_detects_tiktok_short():
    result = detect_url_type("https://vm.tiktok.com/abc123/")
    assert result["platform"] == "tiktok"
    assert result["content_type"] == "video_short"


def test_detects_instagram_reel():
    result = detect_url_type("https://www.instagram.com/reel/abc123/")
    assert result["platform"] == "instagram"
    assert result["content_type"] == "video_short"


def test_detects_instagram_post():
    result = detect_url_type("https://www.instagram.com/p/abc123/")
    assert result["platform"] == "instagram"
    assert result["content_type"] == "carousel"


def test_detects_youtube():
    result = detect_url_type("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["platform"] == "youtube"
    assert result["content_type"] == "video"


def test_detects_youtu_be():
    result = detect_url_type("https://youtu.be/dQw4w9WgXcQ")
    assert result["platform"] == "youtube"
    assert result["content_type"] == "video"


def test_detects_youtube_shorts():
    result = detect_url_type("https://www.youtube.com/shorts/F3nYY3N2wgw")
    assert result["platform"] == "youtube"
    assert result["content_type"] == "video"


def test_detects_linkedin():
    result = detect_url_type("https://www.linkedin.com/posts/user_activity-123")
    assert result["platform"] == "linkedin"
    assert result["content_type"] == "post"


def test_unknown_url_returns_none():
    result = detect_url_type("https://example.com/something")
    assert result is None


# --- parse_vtt_text ---

def test_parse_vtt_strips_timecodes():
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
Привет это первая строка

00:00:03.000 --> 00:00:05.000
И это вторая строка
"""
    result = parse_vtt_text(vtt_content)
    assert "Привет это первая строка" in result
    assert "И это вторая строка" in result
    assert "-->" not in result
    assert "WEBVTT" not in result


def test_parse_vtt_deduplicates_lines():
    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
Повторяющаяся строка

00:00:02.000 --> 00:00:04.000
Повторяющаяся строка

00:00:04.000 --> 00:00:06.000
Другая строка
"""
    result = parse_vtt_text(vtt_content)
    assert result.count("Повторяющаяся строка") == 1


# --- process_url (mocked yt-dlp) ---

def test_process_url_tiktok_success():
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nTest content\n"

    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("builtins.open", mock_open(read_data=vtt_content)), \
         patch("content_bot.services.content_processor.os.remove"):

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.side_effect = [["/tmp/abc123.ru.vtt"], []]  # first call finds .vtt

        result = process_url("https://www.tiktok.com/@user/video/123")

    assert result is not None
    assert result.platform == "tiktok"
    assert result.content_type == "video_short"
    assert "Test content" in result.transcript


def test_process_url_unknown_returns_none():
    result = process_url("https://example.com/not-supported")
    assert result is None


def test_process_url_no_subtitles_returns_content_without_transcript():
    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("content_bot.services.content_processor.tempfile.TemporaryDirectory") as mock_tmpdir:

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.return_value = []  # no subtitle files found
        mock_tmpdir.return_value.__enter__ = MagicMock(return_value="/tmp/fake")
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        result = process_url("https://www.youtube.com/watch?v=abc123")

    assert result is not None
    assert result.platform == "youtube"
    assert result.transcript is None


# --- proxy support ---

def test_extract_subtitles_passes_proxy_when_set():
    """When WEBSHARE_PROXY_URL is set, --proxy flag appears in yt-dlp command."""
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\n"

    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("builtins.open", mock_open(read_data=vtt_content)), \
         patch("content_bot.services.content_processor.os.remove"), \
         patch("content_bot.config.WEBSHARE_PROXY_URL", "http://user:pass@p.webshare.io:80"):

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.side_effect = [["/tmp/abc.vtt"], []]

        process_url("https://www.tiktok.com/@user/video/123")

        cmd = mock_run.call_args[0][0]
        assert "--proxy" in cmd
        assert "http://user:pass@p.webshare.io:80" in cmd


def test_extract_subtitles_no_proxy_when_not_set():
    """When WEBSHARE_PROXY_URL is not set, --proxy is absent from yt-dlp command."""
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\n"

    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("builtins.open", mock_open(read_data=vtt_content)), \
         patch("content_bot.services.content_processor.os.remove"), \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.side_effect = [["/tmp/abc.vtt"], []]

        process_url("https://www.tiktok.com/@user/video/123")

        cmd = mock_run.call_args[0][0]
        assert "--proxy" not in cmd


# --- _extract_carousel_text ---

def test_extract_carousel_text_structures_slides():
    """Multiple downloaded images produce [Слайд N] markers in order."""
    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("content_bot.services.vision.extract_text_from_image") as mock_ocr, \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=0)
        # glob called 4 times (jpg, jpeg, png, webp)
        mock_glob.side_effect = [
            ["/tmp/fake/1.jpg", "/tmp/fake/2.jpg"],
            [],
            [],
            [],
        ]
        mock_ocr.side_effect = ["Текст первого слайда", "Текст второго слайда"]

        result = _extract_carousel_text("https://www.instagram.com/p/abc123/")

    assert result is not None
    assert "[Слайд 1]\nТекст первого слайда" in result
    assert "[Слайд 2]\nТекст второго слайда" in result


def test_extract_carousel_text_returns_none_when_no_images():
    """Returns None if yt-dlp downloads nothing."""
    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=1)
        mock_glob.return_value = []

        result = _extract_carousel_text("https://www.instagram.com/p/abc123/")

    assert result is None


def test_extract_carousel_text_returns_none_when_all_ocr_empty():
    """Returns None if all images have no text."""
    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("content_bot.services.vision.extract_text_from_image") as mock_ocr, \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.side_effect = [["/tmp/fake/1.jpg"], [], [], []]
        mock_ocr.return_value = ""

        result = _extract_carousel_text("https://www.instagram.com/p/abc123/")

    assert result is None


def test_process_url_instagram_carousel_routes_to_ocr():
    """Instagram p/ (carousel) goes to instaloader first, skips audio pipeline."""
    with patch("content_bot.services.content_processor._extract_instagram_carousel") as mock_insta, \
         patch("content_bot.services.content_processor._extract_carousel_text") as mock_carousel, \
         patch("content_bot.services.content_processor._extract_subtitles") as mock_subs, \
         patch("content_bot.services.content_processor._extract_with_groq") as mock_groq:

        mock_insta.return_value = "[Слайд 1]\nИнфографика"

        result = process_url("https://www.instagram.com/p/abc123/")

    mock_insta.assert_called_once_with("https://www.instagram.com/p/abc123/")
    mock_subs.assert_not_called()
    mock_groq.assert_not_called()
    assert result.platform == "instagram"
    assert result.content_type == "carousel"
    assert result.transcript == "[Слайд 1]\nИнфографика"


def test_process_url_tiktok_falls_back_to_carousel_when_no_audio():
    """TikTok with no audio/subtitles tries _extract_carousel_text as final fallback."""
    with patch("content_bot.services.content_processor._extract_subtitles") as mock_subs, \
         patch("content_bot.services.content_processor._extract_with_groq") as mock_groq, \
         patch("content_bot.services.content_processor._extract_carousel_text") as mock_carousel:

        mock_subs.return_value = None
        mock_groq.return_value = None
        mock_carousel.return_value = "[Слайд 1]\nТекст из слайда"

        result = process_url("https://www.tiktok.com/@user/video/123")

    mock_carousel.assert_called_once()
    assert result.transcript == "[Слайд 1]\nТекст из слайда"
