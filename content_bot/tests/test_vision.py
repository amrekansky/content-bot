import io
import pytest
from unittest.mock import patch, MagicMock
from content_bot.services.vision import extract_text_from_image, extract_text_from_pdf


def test_extract_text_from_image_returns_string():
    mock_response = MagicMock()
    mock_response.full_text_annotation.text = "Hello from image"

    with patch("content_bot.services.vision.vision.ImageAnnotatorClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.document_text_detection.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = extract_text_from_image(b"fake_image_bytes")

    assert result == "Hello from image"


def test_extract_text_from_image_empty_returns_empty():
    mock_response = MagicMock()
    mock_response.full_text_annotation.text = ""

    with patch("content_bot.services.vision.vision.ImageAnnotatorClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.document_text_detection.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = extract_text_from_image(b"empty_image")

    assert result == ""


def test_extract_text_from_pdf_multiple_pages():
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page one"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page two"
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page1, mock_page2]

    with patch("content_bot.services.vision.pdfplumber.open", return_value=mock_pdf):
        result = extract_text_from_pdf(b"fake_pdf_bytes")

    assert "Page one" in result
    assert "Page two" in result


def test_extract_text_from_pdf_empty_pages_returns_empty():
    mock_page = MagicMock()
    mock_page.extract_text.return_value = None
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("content_bot.services.vision.pdfplumber.open", return_value=mock_pdf):
        result = extract_text_from_pdf(b"empty_pdf")

    assert result == ""
