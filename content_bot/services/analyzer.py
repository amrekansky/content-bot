import logging
import time
import google.generativeai as genai

from content_bot.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

_PROMPT = """\
Проанализируй контент и верни структурированный разбор.

Контент: {platform} | {content_type}
{transcript}

Верни текст в формате:
Хук: <первые 1-2 предложения / первые 3-5 секунд>
Структура: <как построен контент, 1-2 предложения>
CTA: <что просят сделать в конце>
Тон: <стиль автора, 1 предложение>
Главная идея: <одна идея которую можно адаптировать>
Потенциал адаптации: <высокий / средний / низкий>
Заметки: <почему такой потенциал и как адаптировать для headlessaimode, 2-3 предложения>\
"""

_MAX_RETRIES = 3
_RETRY_DELAY = 20  # seconds to wait on 429


def analyze(transcript: str, platform: str, content_type: str) -> str | None:
    """Analyze transcript via Gemini Flash. Returns plain text or None."""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, skipping analysis")
        return None
    if not transcript or not transcript.strip():
        return None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = _PROMPT.format(
                platform=platform,
                content_type=content_type,
                transcript=transcript[:8000],
            )
            response = model.generate_content(prompt)
            return response.text.strip() or None
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "resource_exhausted" in err.lower():
                if attempt < _MAX_RETRIES:
                    logger.warning("Gemini quota hit, retrying in %ds (attempt %d/%d)",
                                   _RETRY_DELAY, attempt, _MAX_RETRIES)
                    time.sleep(_RETRY_DELAY)
                    continue
            logger.warning("Gemini analysis failed: %s", e, exc_info=True)
            return None
    return None
