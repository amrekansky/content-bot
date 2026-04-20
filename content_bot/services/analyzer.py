import logging
import anthropic

from content_bot.config import ANTHROPIC_API_KEY

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


def analyze(transcript: str, platform: str, content_type: str) -> str | None:
    """Analyze transcript via Claude Haiku. Returns plain text or None."""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set, skipping analysis")
        return None
    if not transcript or not transcript.strip():
        return None
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = _PROMPT.format(
            platform=platform,
            content_type=content_type,
            transcript=transcript[:8000],
        )
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        return text or None
    except Exception as e:
        logger.warning("Claude analysis failed: %s", e, exc_info=True)
        return None
