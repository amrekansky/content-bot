import json
import logging
from pathlib import Path

import anthropic

from content_bot.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_VOICE_DIR = Path(__file__).parent.parent / "voice"


def _load_voice() -> str:
    about = (_VOICE_DIR / "about.md").read_text(encoding="utf-8").strip()
    examples = []
    for f in sorted((_VOICE_DIR / "examples").glob("*.md")):
        examples.append(f.read_text(encoding="utf-8").strip())
    examples_block = "\n\n".join(f"=== Пример ===\n{e}" for e in examples)
    return f"Голос автора:\n{about}\n\nПримеры постов:\n{examples_block}"


_VOICE_CONTEXT = _load_voice()

_SYSTEM_PROMPT = f"""\
Ты пишешь контент от первого лица для автора канала @headlessaimode.

{_VOICE_CONTEXT}

Пиши точно в этом голосе. Никаких длинных тире как разрыв предложения. Без буллетов если не указано. Без хэштегов. Короткие абзацы. Честный разговорный тон.

ВАЖНО: всегда отвечай валидным JSON без markdown-блоков:
{{"hook": "первые 1-2 предложения поста", "content": "полный текст поста включая хук"}}\
"""

_PLATFORM_PROMPTS = {
    "tiktok": """\
Напиши сценарий для TikTok/Reels в моем голосе на основе анализа и транскрипта.
Длина: 60-90 секунд. Структура: хук (первые 3 сек) → проблема → решение → CTA.
Без хэштегов. Разговорный стиль, как будто говоришь на камеру.

Анализ: {analysis}
Транскрипт: {transcript}""",

    "telegram": """\
Напиши пост для Telegram-канала в моем голосе на основе анализа и транскрипта.
Длина: 150-300 слов. Только абзацы, без буллетов и списков. Заканчивается одним CTA.

Анализ: {analysis}
Транскрипт: {transcript}""",

    "linkedin": """\
Напиши LinkedIn пост в моем голосе на основе анализа и транскрипта.
Длина: 150-250 слов. Первая строка — хук. Профессиональный но живой тон. Без хэштегов.

Анализ: {analysis}
Транскрипт: {transcript}""",

    "youtube": """\
Напиши скрипт для YouTube видео в моем голосе на основе анализа и транскрипта.
Длина: 5-8 минут (800-1200 слов). Структура: хук → проблема → история → решение → CTA.
Разговорный стиль.

Анализ: {analysis}
Транскрипт: {transcript}""",
}

_PLATFORM_FORMAT = {
    "tiktok": ("TikTok", "TikTok"),
    "telegram": ("Telegram", "Telegram Long"),
    "linkedin": ("LinkedIn", "LinkedIn Long"),
    "youtube": ("YouTube", "YouTube Long"),
}


def generate(transcript: str, analysis: str, platform: str) -> dict | None:
    """Generate a platform script via Claude Haiku.

    Returns {"hook": str, "content": str, "platform_label": str, "format_label": str} or None.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set, skipping generation")
        return None
    if platform not in _PLATFORM_PROMPTS:
        logger.warning("Unknown platform: %s", platform)
        return None
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        user_prompt = _PLATFORM_PROMPTS[platform].format(
            analysis=analysis[:2000],
            transcript=transcript[:6000],
        )
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
        data = json.loads(raw)
        platform_label, format_label = _PLATFORM_FORMAT[platform]
        return {
            "hook": data.get("hook", ""),
            "content": data.get("content", ""),
            "platform_label": platform_label,
            "format_label": format_label,
        }
    except json.JSONDecodeError:
        logger.warning("Claude returned non-JSON for %s, storing raw text", platform)
        platform_label, format_label = _PLATFORM_FORMAT[platform]
        return {
            "hook": "",
            "content": raw,
            "platform_label": platform_label,
            "format_label": format_label,
        }
    except Exception as e:
        logger.warning("Claude generation failed for %s: %s", platform, e, exc_info=True)
        return None
