import io
import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_FONT_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"
_W, _H = 1080, 1080
_BG = (13, 17, 23)
_TEXT = (230, 237, 243)
_ACCENT = (88, 166, 255)
_DIM = (110, 118, 129)
_PADDING = 80
_FONT_SIZE_HOOK = 52
_FONT_SIZE_WATERMARK = 28
_LINE_HEIGHT = 70
_MAX_CHARS_PER_LINE = 28


def _load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    candidates = [
        (_FONT_DIR / "Inter-Bold.ttf", _FONT_DIR / "Inter-Regular.ttf"),
        (_FONT_DIR / "FiraCode-Bold.ttf", _FONT_DIR / "FiraCode-Regular.ttf"),
    ]
    for bold_path, regular_path in candidates:
        try:
            bold = ImageFont.truetype(str(bold_path), _FONT_SIZE_HOOK)
            regular = ImageFont.truetype(str(regular_path), _FONT_SIZE_WATERMARK)
            return bold, regular
        except Exception:
            continue
    logger.warning("No bundled fonts found, using Pillow default")
    default = ImageFont.load_default()
    return default, default


def _extract_hook(script_text: str) -> str:
    for para in script_text.split("\n"):
        para = para.strip()
        if para:
            return para[:200]
    return script_text[:200].strip()


def generate_card(script_text: str) -> bytes:
    """Generate a 1080x1080 dark branded card with the hook as overlay text.

    Returns PNG bytes.
    """
    img = Image.new("RGB", (_W, _H), _BG)
    draw = ImageDraw.Draw(img)

    font_hook, font_watermark = _load_fonts()

    hook = _extract_hook(script_text)
    lines = textwrap.wrap(hook, width=_MAX_CHARS_PER_LINE) or [""]

    total_text_h = len(lines) * _LINE_HEIGHT
    text_start_y = (_H - total_text_h) // 2

    # Blue accent line above text
    accent_y = text_start_y - 20
    draw.rectangle([_PADDING, accent_y, _W - _PADDING, accent_y + 4], fill=_ACCENT)

    # Hook lines centered
    y = text_start_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_hook)
        text_w = bbox[2] - bbox[0]
        x = (_W - text_w) // 2
        draw.text((x, y), line, font=font_hook, fill=_TEXT)
        y += _LINE_HEIGHT

    # Watermark bottom-right
    watermark = "@headlessaimode"
    wm_bbox = draw.textbbox((0, 0), watermark, font=font_watermark)
    wm_w = wm_bbox[2] - wm_bbox[0]
    draw.text((_W - _PADDING - wm_w, _H - _PADDING), watermark, font=font_watermark, fill=_DIM)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
