# Content Bot

Telegram-бот принимает ссылки (TikTok, YouTube, Reels, LinkedIn) и медиафайлы.
Вытаскивает текст, сохраняет в PostgreSQL-библиотеку, форвардит карточку в приватный архив-канал.

## Что умеет

- Принимает ссылки: TikTok, Reels, YouTube, LinkedIn
- Принимает фото, скриншоты, PDF-файлы
- Вытаскивает субтитры через yt-dlp (YouTube/Reels) или транскрибирует аудио (fallback)
- OCR для изображений и PDF через Google Vision API
- Сохраняет транскрипт в PostgreSQL
- Форвардит карточку в приватный Telegram-канал (архив)

## Стек

Python · python-telegram-bot · PostgreSQL · yt-dlp · Google Vision API · Render

## Как я это строил

→ [TUTORIAL.md](TUTORIAL.md)

## Попробовать

→ [@headlessaimode_bot](https://t.me/headlessaimode_bot)
