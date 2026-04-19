# Module 2 Redesign — комната-идей pipeline

## Goal

Заменить текущий Module 2 (Gemini анализ → Sheets → поллер) на inline-пайплайн: один Groq-вызов делает анализ + генерирует 8 единиц контента в голосе автора сразу при инжесте. Поллер удаляется. Sheets остается как dashboard.

## Why redesign

Текущее решение не работает:
- Gemini 2.0 Flash free tier — дневная квота исчерпывается быстро
- YouTube transcript extraction — yt-dlp блокируется на Render
- Поллер + checkout flow — лишняя сложность, которая добавляет точки отказа

Рабочий reference: файлы в `комната-идей/` — transcript → структурированный анализ → адаптация в голосе автора → стратегические заметки.

## Architecture

Один новый сервис — `composer.py` — принимает транскрипт и отдает полный комплект контента за один Groq API call. Поллер, generator.py и checkbox-колонки в Sheets удаляются.

```
URL / file
    ↓
content_ingest.py
    ↓
content_processor.py   (без изменений — транскрипция)
    ↓
composer.py            (новый — Groq Llama 3.3 70B)
    ├── анализ: Хук / Структура / CTA / Тон / Главная идея
    ├── youtube_long   (2-3 мин, разговорный)
    ├── youtube_short  (60s, хук-first)
    ├── tiktok         (30-45s, быстрый темп)
    ├── shorts         (30-45s, визуальные хуки)
    ├── linkedin_long  (пост со сторителлингом)
    ├── linkedin_short (2-3 абзаца, прямо к делу)
    ├── telegram_long  (полный пост со структурой)
    ├── telegram_short (короткий удар)
    └── notes          (что сработало, идеи)
    ↓
sheets.py              (обновленные колонки — пишет всё сразу)
    ↓
content_ingest.py      (форвард в архив-канал — полный markdown)
```

## LLM

**Groq Llama 3.3 70B** — уже в requirements.txt и env vars. Бесплатный tier: 500 req/day, 6000 req/min. Один вызов на инжест.

Транскрипция остается на Groq Whisper (уже работает в `_extract_with_groq`).

## Voice Context

Hardcode в `composer.py` как module-level константа `_VOICE_CONTEXT`. Содержит:

1. **Профиль голоса** — полный текст из `04-sales/linkedin-about-ru.md`
2. **Пример 1** — `04-sales/telegram-channel/post-kto-ya.md` (личная история + боль)
3. **Пример 2** — `04-sales/telegram-channel/post-what-is-headless.md` (объяснение концепции)
4. **Пример 3** — `04-sales/telegram-channel/post-content-bot.md` (проектный пост)

Голос: прямой, без воды, с личными историями и конкретными деталями, разговорный стиль, технические термины без объяснений, антихайп.

## Groq Prompt Structure

```
System prompt:
  Ты стратег контента. Работай строго в голосе автора.
  [VOICE PROFILE] {linkedin_about}
  [TELEGRAM EXAMPLES] {post_1} {post_2} {post_3}

User prompt:
  Платформа источника: {platform}
  Тип: {content_type}
  Транскрипт: {transcript[:6000]}

  Верни JSON со следующими ключами:
  analysis_hook, analysis_structure, analysis_cta,
  analysis_tone, analysis_main_idea,
  youtube_long, youtube_short, tiktok, shorts,
  linkedin_long, linkedin_short,
  telegram_long, telegram_short,
  notes
```

Groq возвращает JSON → `composer.py` парсит → возвращает dataclass `ComposedContent`.

## File Changes

**Удалить:**
- `content_bot/tasks/poller.py`
- `content_bot/services/generator.py`

**Создать:**
- `content_bot/services/composer.py` — Groq вызов + голос + парсинг JSON

**Изменить:**
- `content_bot/services/analyzer.py` — удалить (логика переезжает в composer.py)
- `content_bot/services/sheets.py` — новые колонки, убрать checkbox логику
- `content_bot/handlers/content_ingest.py` — вызов composer вместо analyzer+generator, форвард markdown в архив-канал
- `bot.py` — убрать регистрацию poller job

**Тесты:**
- `content_bot/tests/test_composer.py` — новые
- `content_bot/tests/test_sheets.py` — обновить под новые колонки
- `content_bot/tests/test_analyzer.py` — удалить

## Sheets Columns (новые)

```
ID | URL | Платформа | Название | Дата | Статус |
Хук | YouTube Long | YouTube Short | TikTok | Shorts |
LinkedIn Long | LinkedIn Short | Telegram Long | Telegram Short |
Заметки
```

Итого 16 колонок (было 16 — те же позиции, другое содержание).

Статусы: `обработка` → `готово` / `нет транскрипта` / `ошибка анализа`

Checkbox-колонки и скриптовые колонки старого формата заменяются контентными.

**Миграция:** обновить заголовки вручную в Google Sheets (удалить строку 1, вставить новую). Старые строки данных становятся несовместимыми — очистить Sheet перед первым запуском.

## Archive Channel Message

После записи в Sheets — форвардим в архив-канал сообщение в комната-идей формате:

```
📍 {platform} | {content_type}
🔗 {url}

**Анализ**
Хук: ...
Структура: ...
CTA: ...
Тон: ...

**YouTube (длинный)**
...

**TikTok**
...

[остальные форматы]

**Заметки**
...
```

Telegram лимит 4096 символов — если больше, шлем двумя сообщениями.

## Error Handling

- Нет транскрипта → пишем в Sheets статус `нет транскрипта`, не вызываем composer
- Groq вернул невалидный JSON → retry 1 раз, потом статус `ошибка анализа`
- Groq 429 → retry с задержкой 10s, до 3 попыток
- Sheets недоступен → логируем, не падаем (транскрипт уже в DB)

## Out of Scope

- Локальные markdown файлы в `комната-идей/` — бот на Render не может писать на локальный Mac
- Instagram reels — остается как есть (ждет throwaway аккаунт)
- TikTok карусели — yt-dlp не поддерживает `/photo/` URL
