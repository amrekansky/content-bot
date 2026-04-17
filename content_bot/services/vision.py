import io
import pdfplumber
from google.cloud import vision
from content_bot.config import GOOGLE_VISION_API_KEY


def extract_text_from_image(image_source: bytes | str) -> str:
    """Extract text from image bytes or file path using Google Vision API."""
    if isinstance(image_source, str):
        with open(image_source, "rb") as f:
            image_bytes = f.read()
    else:
        image_bytes = image_source
    client = vision.ImageAnnotatorClient(
        client_options={"api_key": GOOGLE_VISION_API_KEY}
    )
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)
    return response.full_text_annotation.text or ""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    pages_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
    return "\n\n".join(pages_text)
