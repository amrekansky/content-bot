import re
from telegram import Update
from telegram.ext import ContextTypes

from content_bot.config import LIBRARY_CHANNEL_ID
from content_bot.database.db import init_db, insert_content
from content_bot.services.content_processor import process_url
from content_bot.services.vision import extract_text_from_image, extract_text_from_pdf

_URL_RE = re.compile(r"https?://\S+")


def _is_url(text: str) -> bool:
    return bool(_URL_RE.match(text.strip()))


def _build_archive_card(content_id: int, platform: str, content_type: str,
                        source_url: str, transcript: str | None) -> str:
    preview = ""
    if transcript:
        preview = transcript[:200].replace("\n", " ")
        if len(transcript) > 200:
            preview += "..."

    return (
        f"📎 {platform.capitalize()} | {content_type}\n"
        f"🔗 {source_url}\n\n"
        f"📝 {preview or '(нет транскрипта)'}\n\n"
        f"#{content_id}"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    init_db()
    message = update.message

    # URL message
    if message.text and _is_url(message.text):
        url = message.text.strip()
        await message.reply_text("⏳ Обрабатываю...")

        result = process_url(url)
        if result is None:
            await message.reply_text(
                "❌ Ссылка не поддерживается.\n"
                "Принимаю: TikTok, Reels, YouTube, LinkedIn"
            )
            return

        content_id = insert_content(
            source_url=result.source_url,
            platform=result.platform,
            content_type=result.content_type,
            transcript=result.transcript,
        )

        reply = f"✅ Сохранено #{content_id}\n📎 {result.platform} | {result.content_type}"
        if result.transcript:
            preview = result.transcript[:100].replace("\n", " ")
            reply += f"\n📝 {preview}..."

        await message.reply_text(reply)

        card = _build_archive_card(
            content_id=content_id,
            platform=result.platform,
            content_type=result.content_type,
            source_url=result.source_url,
            transcript=result.transcript,
        )
        await context.bot.send_message(chat_id=LIBRARY_CHANNEL_ID, text=card)
        return

    # Photo message
    if message.photo:
        await message.reply_text("⏳ Обрабатываю изображение...")
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        transcript = extract_text_from_image(bytes(image_bytes))

        content_id = insert_content(
            source_url=f"tg://photo/{photo.file_id}",
            platform="telegram",
            content_type="image",
            transcript=transcript or None,
        )

        reply = f"✅ Сохранено #{content_id}\n📷 Изображение"
        if transcript:
            reply += f"\n📝 {transcript[:100]}..."
        await message.reply_text(reply)

        card = _build_archive_card(content_id, "telegram", "image",
                                   f"tg://photo/{photo.file_id}", transcript)
        await context.bot.send_message(chat_id=LIBRARY_CHANNEL_ID, text=card)
        return

    # Document message (PDF or image file)
    if message.document:
        mime = message.document.mime_type or ""
        await message.reply_text("⏳ Обрабатываю файл...")
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await file.download_as_bytearray()

        if mime == "application/pdf":
            transcript = extract_text_from_pdf(bytes(file_bytes))
            content_type = "document"
        elif mime.startswith("image/"):
            transcript = extract_text_from_image(bytes(file_bytes))
            content_type = "image"
        else:
            await message.reply_text("❌ Формат не поддерживается. Принимаю: PDF, изображения")
            return

        content_id = insert_content(
            source_url=f"tg://document/{message.document.file_id}",
            platform="telegram",
            content_type=content_type,
            transcript=transcript or None,
        )

        reply = f"✅ Сохранено #{content_id}\n📄 {content_type.capitalize()}"
        if transcript:
            reply += f"\n📝 {transcript[:100]}..."
        await message.reply_text(reply)

        card = _build_archive_card(content_id, "telegram", content_type,
                                   f"tg://document/{message.document.file_id}", transcript)
        await context.bot.send_message(chat_id=LIBRARY_CHANNEL_ID, text=card)
