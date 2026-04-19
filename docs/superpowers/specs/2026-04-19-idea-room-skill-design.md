# idea-room Skill Design

## Goal

Глобальный Claude Code скил для сбора и переработки контента из соцсетей. Принимает URL или локальный файл, транскрибирует, анализирует в комната-идей формате, генерирует 8 адаптаций в голосе автора, сохраняет markdown локально и обновляет два Google Sheets: Library (источники) и Content Calendar (расписание публикаций).

## Расположение

`~/.claude/skills/idea-room/SKILL.md` — глобальный скил, доступен из любого проекта.

Сохраняет файлы в: `/Users/amrekanski/ai-consultant/комната-идей/`

## Вызов

```bash
idea-room                    # очередь: читает Library Sheets, обрабатывает все необработанные
idea-room <url>              # прямой URL: TikTok, Instagram, YouTube, вебсайт
idea-room <filepath>         # локальный файл: .mp4, .mp3, .jpg, .png, .pdf
```

## Извлечение контента по типу

| Тип входа | Метод | Зависимости |
|-----------|-------|-------------|
| YouTube URL | `youtube-transcript-api` — тянет готовый транскрипт без скачивания | `pip install youtube-transcript-api` |
| TikTok / Instagram URL | `yt-dlp` скачивает видео во временную папку → `mlx-whisper` транскрибирует → папка удаляется | `yt-dlp`, `mlx-whisper` |
| Вебсайт / статья | WebFetch → Claude читает текст страницы | встроено в Claude Code |
| Скриншот / картинка (URL или файл) | Claude Vision через Read tool | встроено в Claude Code |
| PDF (URL или файл) | Claude Read tool — нативная поддержка PDF | встроено в Claude Code |
| Локальный видео/аудио файл | `mlx-whisper` напрямую → temp файлы удаляются | `mlx-whisper` |

**Временные файлы:** `tempfile.mkdtemp()` создает `/tmp/idea-room-xxx/`. Видео скачивается туда, транскрибируется, папка удаляется в `finally` блоке — даже если произошла ошибка. На диске ничего не остается.

**Определение типа:**
- Содержит `youtube.com` или `youtu.be` → YouTube
- Содержит `tiktok.com` → TikTok
- Содержит `instagram.com` → Instagram
- Расширение `.mp4`, `.mp3`, `.mov`, `.m4a`, `.wav` → локальный аудио/видео
- Расширение `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` → изображение
- Расширение `.pdf` → PDF
- Иначе → вебсайт (WebFetch)

## Голос автора

Скил читает локальные файлы при каждом запуске — не hardcode:

```
/Users/amrekanski/ai-consultant/04-sales/linkedin-about-ru.md
/Users/amrekanski/ai-consultant/04-sales/telegram-channel/post-kto-ya.md
/Users/amrekanski/ai-consultant/04-sales/telegram-channel/post-what-is-headless.md
/Users/amrekanski/ai-consultant/04-sales/telegram-channel/post-content-bot.md
```

Голос: прямой, без воды, личные истории с конкретными деталями, технические термины без объяснений, антихайп, разговорный стиль.

## Анализ и генерация (один Claude вызов)

Claude в текущей сессии делает анализ и генерацию за один раз.

**Промпт структура:**
```
[VOICE PROFILE] содержимое linkedin-about-ru.md
[EXAMPLES] три telegram поста

Проанализируй контент и адаптируй в голосе автора.

Платформа источника: {platform}
Транскрипт: {transcript}

Верни структурированный результат:
АНАЛИЗ
Хук: ...
Структура: ...
CTA: ...
Тон: ...
Главная идея: ...

YOUTUBE ДЛИННЫЙ (2-3 мин, разговорный, с личной историей)
...

YOUTUBE КОРОТКИЙ (60s, хук-first, быстрый темп)
...

TIKTOK (30-45s, быстрый темп, визуальные хуки)
...

SHORTS (30-45s, вертикальный формат, хук в первые 3 секунды)
...

LINKEDIN ДЛИННЫЙ (пост со сторителлингом, 3-5 абзацев)
...

LINKEDIN КОРОТКИЙ (2-3 абзаца, прямо к делу)
...

TELEGRAM ДЛИННЫЙ (полный пост со структурой и CTA)
...

TELEGRAM КОРОТКИЙ (короткий удар, 3-5 предложений)
...

ЗАМЕТКИ
Что сработало в оригинале: ...
Идеи для контента: ...
```

## Выходной файл (комната-идей)

Путь: `/Users/amrekanski/ai-consultant/комната-идей/YYYY-MM-DD_<slug>.md`

Slug: первые 5 слов заголовка/хука, lowercase, через дефис.

Формат файла:
```markdown
# {главная идея одной строкой}

**Источник:** {url или filepath}
**Дата:** {YYYY-MM-DD}
**Метод транскрипции:** {youtube-api / whisper / vision / webfetch}
**Язык оригинала:** {EN / RU}

---

## Анализ оригинала

**Хук:** ...
**Структура:** ...
**CTA:** ...
**Тон:** ...
**Главная идея:** ...

---

## Адаптация в твоем голосе

### YouTube (длинный)
...

### YouTube (короткий)
...

### TikTok
...

### Shorts
...

### LinkedIn (длинный)
...

### LinkedIn (короткий)
...

### Telegram (длинный)
...

### Telegram (короткий)
...

---

## Заметки

**Что сработало в оригинале:**
...

**Идеи для контента:**
...
```

## Library Sheets — обновление статуса

После успешной обработки: скил обновляет колонку `Статус` в Library Sheets с `новый` → `обработано`.

Credentials: читает из `~/.env` или переменной окружения `GOOGLE_SHEETS_CREDENTIALS` + `GOOGLE_SHEETS_LIBRARY_ID`.

## Content Calendar Sheets — авто-расписание

**Новый отдельный Sheets.** Скил добавляет 8 строк (по одной на формат).

**Колонки:**
```
Дата | Платформа | Формат | Хук | Контент | Статус | Источник URL | Файл
```

**Авто-расписание** (от даты обработки, ближайший свободный слот):

| Формат | Сдвиг |
|--------|-------|
| TikTok | +1 день |
| Shorts | +2 дня |
| Telegram Short | +2 дня |
| Telegram Long | +3 дня |
| LinkedIn Short | +4 дня |
| LinkedIn Long | +5 дней |
| YouTube Short | +7 дней |
| YouTube Long | +14 дней |

Если слот занят — сдвигает на следующий день. Пользователь может менять даты вручную в Sheets.

**Статусы:** `черновик` → `готово` → `опубликовано`

## Режим очереди (idea-room без аргументов)

1. Читает Library Sheets
2. Фильтрует строки где Статус = `новый` или `обработка`
3. Для каждой строки: выводит прогресс → обрабатывает → сохраняет → обновляет Sheets
4. Итог: N обработано, M пропущено (нет транскрипта), K ошибок

## Error handling

- YouTube API не вернул транскрипт → пробуем yt-dlp + mlx-whisper как fallback
- yt-dlp не смог скачать → логируем URL, продолжаем очередь
- Whisper не смог транскрибировать → статус `ошибка транскрипции` в Library Sheets
- Sheets недоступен → сохраняем markdown локально, выводим предупреждение
- Временные файлы всегда удаляются (try/finally)

## Зависимости (локальные, Mac)

```bash
pip install yt-dlp youtube-transcript-api gspread
pip install mlx-whisper   # Apple Silicon
```

## Out of Scope

- Публикация контента напрямую в соцсети — только подготовка черновиков
- Instagram reels / TikTok карусели — те же ограничения что и в боте
- Windows / Linux — только macOS (mlx-whisper)
