# Как я запилил Content Bot с нуля в Claude Code

> Это живая документация — пишется параллельно с кодом.
> Каждый шаг: что делаю, почему, какие команды запускаю.

---

## Что строим

Бот принимает ссылки и медиафайлы. Транскрибирует, сохраняет в базу, форвардит в приватный архив-канал. Дальше — генерирует контент под твой голос (Модуль 2, отдельно).

**Что работает сейчас:**
- YouTube видео — транскрипт через youtube-transcript-api или Groq Whisper
- TikTok видео — транскрипт через Groq Whisper (аудио через прокси)
- Фото и PDF — текст через Google Vision OCR

**Что не работает (и почему):**
- Instagram (reels и карусели) — Instagram блокирует все автоматические запросы без авторизации. Это не баг, это их политика. Без аккаунта — никак.
- TikTok карусели (посты со слайдами) — yt-dlp не поддерживает `/photo/` URL-формат.

---

## Что понадобится

- Claude Code (подписка на claude.ai/code)
- Аккаунт Telegram
- Аккаунт GitHub
- Аккаунт Render (бесплатный tier)
- Google Cloud аккаунт (для Vision API)

---

## Шаг 1 — Режим мудреца: из идеи в архитектуру

Любой проект начинается не с кода, а с понимания что именно строишь.
Я зашел в Claude Code и запустил `/brainstorming` — это "режим мудреца".

```bash
claude
/brainstorming проаудировать несколько Telegram каналов и воплотить лучшие идеи
```

Claude не выдает решение сразу. Задает вопросы по одному:
- Зачем тебе библиотека контента?
- Как ты сейчас сохраняешь интересные видео?
- Что происходит после сохранения — ты к этому возвращаешься?

Каждый ответ сужает задачу. Через 20 минут диалога вышел полный дизайн-спец:
три модуля, SQL-схема, файловая структура, список env-переменных.

Это и есть headless режим: не гуглить паттерны, а думать вслух с AI пока не появится форма.

Если застрял — сделай скриншот и кинь в терминал Claude Code. Агент разберется.

---

## Шаг 2 — Внешние сервисы (20 минут)

Перед кодом нужно настроить четыре внешних сервиса. Займет минут 20.

**Telegram BotFather:**

Зайди в Telegram → найди @BotFather → отправь `/newbot` → придумай имя → скопируй токен.
Токен выглядит так: `1234567890:ABCdefGHIjklMNOpqrSTUvwxyz`

Если застрял — скриншот в Claude Code.

**PostgreSQL на Render:**

1. render.com → New → PostgreSQL
2. Бесплатный план (Free)
3. После создания: вкладка Info → скопируй **External Database URL**

URL выглядит так: `postgresql://user:pass@host.render.com/dbname`

Если застрял — скриншот в Claude Code.

**Google Vision API:**

1. console.cloud.google.com → создай новый проект
2. APIs & Services → Enable APIs → найди "Cloud Vision API" → Enable
3. Credentials → Create Credentials → API Key → скопируй

Если застрял — скриншот в Claude Code.

**GitHub репо:**

1. github.com → New repository
2. Назови `content-bot` → Public → Create
3. Склонируй локально:

```bash
git clone https://github.com/[твой-username]/content-bot
cd content-bot
```

Если застрял — скриншот в Claude Code.

---

## Шаг 3 — План имплементации

После проектирования — план имплементации.

Запускаю `/writing-plans` скил в Claude Code:

```bash
claude
/writing-plans docs/superpowers/specs/2026-04-14-content-ingest-library-design.md
```

Скил читает спец и разбивает на задачи по 5-10 минут. Каждая задача — чекбокс:
тест → реализация → тест прошел → коммит.

Это и есть план по которому строится этот бот.
Если застрял — скриншот в Claude Code.

---

## Шаг 4.1 — database/db.py: таблица library_content

Первый файл кода — база данных.

Смотри как работает субагент-driven development:
Claude Code запускает свежий агент на задачу "создай db.py",
тот пишет тест, запускает, реализует, коммитит.
Никакого накопленного контекста — чистый старт на каждую задачу.

Таблица `library_content`:

```sql
CREATE TABLE IF NOT EXISTS library_content (
    id              SERIAL PRIMARY KEY,
    source_url      TEXT NOT NULL,
    platform        VARCHAR(20) NOT NULL,
    content_type    VARCHAR(20) NOT NULL,
    transcript      TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'analyzed',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Три функции: `init_db()`, `insert_content()`, `get_content_by_id()`.
Всё. Больше ничего. YAGNI — You Aren't Gonna Need It.

Если застрял — скриншот в Claude Code.

---

## Шаг 4.2 — services/vision.py: OCR и PDF

`services/vision.py` — две функции:

- `extract_text_from_image(bytes)` → строка текста через Google Vision API
- `extract_text_from_pdf(bytes)` → текст всех страниц через pdfplumber

Никакого сохранения файлов. Принял байты — вернул текст. Чисто.

```python
from content_bot.services.vision import extract_text_from_image, extract_text_from_pdf

text = extract_text_from_image(image_bytes)
text = extract_text_from_pdf(pdf_bytes)
```

Google Vision API подключается через API-ключ из переменной `GOOGLE_VISION_API_KEY`.
Ключ взял из шага 2 — тот же что в основном боте.

Если застрял — скриншот в Claude Code.

---

## Шаг 4.3 — services/content_processor.py: yt-dlp

`services/content_processor.py` — три функции:

- `detect_url_type(url)` → `{platform, content_type}` или `None`
- `parse_vtt_text(vtt_content)` → чистый текст без таймкодов
- `process_url(url)` → `ProcessedContent` с транскриптом

Никакого LLM на этом этапе. Бот — механический сборщик.
Транскрипт извлекается в три попытки:

1. **youtube-transcript-api** — самый быстрый путь для YouTube, без скачивания
2. **Groq Whisper** — скачивает аудио через yt-dlp (mp3, ~64kbps), отправляет в Whisper API
3. **yt-dlp субтитры** — последний резерв, `.vtt` файл без аудио

Для TikTok и Instagram: сначала субтитры через yt-dlp, потом Groq Whisper.
Все yt-dlp вызовы идут через residential proxy (WEBSHARE_PROXY_URL) —
без этого Render'овский datacenter IP блокируется YouTube и TikTok.

```bash
# Что делает yt-dlp под капотом:
yt-dlp --write-auto-sub --sub-lang ru,en --skip-download \
  --output /tmp/%(id)s https://youtube.com/watch?v=...
```

Временный файл субтитров удаляется сразу после чтения. Никакого хранения медиа.

Если застрял — скриншот в Claude Code.

---

## Шаг 4.4 — handlers/content_ingest.py: входящие сообщения

`handlers/content_ingest.py` — один хендлер на все входящие сообщения:

- Ссылка → `process_url()` → сохраняем в DB → карточка в архив-канал
- Фото → `extract_text_from_image()` → сохраняем
- PDF → `extract_text_from_pdf()` → сохраняем

Карточка в архив-канал выглядит так:

```
📎 Youtube | video
🔗 https://youtu.be/...

📝 Первые 200 символов транскрипта...

#42
```

`LIBRARY_CHANNEL_ID` — ID приватного канала куда форвардятся все карточки.
Берешь его через @userinfobot или настройки канала.

Если застрял — скриншот в Claude Code.

---

## Шаг 4.5 — bot.py: сборка и запуск

`bot.py` — точка входа. Три строки логики:

```python
init_db()                                              # создаем таблицу если нет
app = Application.builder().token(BOT_TOKEN).build()   # создаем бота
app.add_handler(MessageHandler(..., handle_message))   # регистрируем хендлер
app.run_polling()                                      # запускаем
```

Запустить локально (нужны все переменные из `.env`):

```bash
cd content-bot
cp .env.example .env
# Заполни .env своими значениями
python3 bot.py
```

Должно написать в консоли: `Bot started — polling`
Открой Telegram → найди своего бота → кинь ссылку → должен ответить `✅ Сохранено #1`

Если застрял — скриншот в Claude Code.

---

## История: три фикса и один диагноз

Бот задеплоился. Карточки сохраняются. Всё выглядит хорошо — но транскрипта нет.
Поле всегда пустое. Ни у YouTube, ни у TikTok.

**Фикс 1.** `youtube-transcript-api` — в версии 0.7+ убрали метод `get_transcript` у класса.
Нашел, переписал на инстанс-метод. Задеплоил. Транскрипта нет.

**Фикс 2.** Добавил Groq Whisper как fallback: скачиваем аудио через yt-dlp, отправляем в Whisper API.
Задеплоил. Транскрипта нет. При этом логи показывают 6 секунд на обработку 34-минутного видео.
Что-то не так на уровне глубже кода.

**Фикс 3.** Добавил Groq Whisper fallback для TikTok и Instagram тоже — вдруг проблема в ветке.
Задеплоил. Транскрипта нет.

Три правильных фикса. Ни один не работает.

---

Вместо Фикса 4 — включил режим мудреца:

```bash
/brainstorming решить проблему транскрипции в content-bot
```

Claude не предложил следующий патч. Задал вопрос: GROQ_API_KEY добавлен на Render?
Да, добавлен. Тогда почему 6 секунд на 34-минутное видео?

Потому что yt-dlp не скачивает аудио. Он падает почти моментально с ошибкой.
YouTube и TikTok детектируют datacenter IP и блокируют на уровне сети.
Render — shared datacenter. Все три фикса атаковали не ту проблему.

**Решение:** residential proxy. Один env var (`WEBSHARE_PROXY_URL`), все платформы фиксируются сразу.

---

Это и есть точка применения режима мудреца — не когда застрял после первой попытки,
а когда три правильных фикса не работают и ты готов писать четвертый.
Именно тогда нужно выйти из режима исполнения и начать диагностировать.

**Итог:** прокси сработал. YouTube и TikTok-видео теперь получают полный транскрипт.

---

После этого — следующий раунд. Instagram. Карусели (слайды с инфографикой) и Reels.

yt-dlp скачивает видео через прокси — но Instagram это не YouTube. У него нет публичного API для контента. Любой запрос без авторизованного аккаунта возвращает "login required". Прокси не помогает — это не проблема IP, это политика закрытого сада.

Код для instaloader (Python-библиотека с логином через username + password) написан и задеплоен. Нужно только добавить два env var на Render — и Instagram заработает. Но это throwaway аккаунт, которого пока нет.

**Решение:** принять ограничение сейчас, добавить в бэклог.

Иногда правильное инженерное решение — это не решить задачу, а признать где проходит граница. Бот делает то, для чего создан: YouTube, TikTok-видео, фото, PDF. Instagram — в бэклоге, под конкретный тикет с конкретным условием (throwaway аккаунт).

---

**Что работает:**
- YouTube видео — транскрипт через youtube-transcript-api или Groq Whisper
- TikTok видео — транскрипт через Groq Whisper (аудио через прокси)
- Фото и PDF — текст через Google Vision OCR

**Что не работает (осознанное ограничение):**
- Instagram reels и карусели — Instagram требует авторизацию, без аккаунта нет доступа
- TikTok карусели (`/photo/` URL) — yt-dlp не поддерживает этот формат

---

## Шаг 5 — Деплой на Render

Последний шаг — запустить бота в облаке.

**render.com → New → Background Worker**

> Важно: выбирай именно **Background Worker**, не Web Service.
> Web Service ждет HTTP-сервер на порту — polling-бот его не запускает, и Render убивает процесс.

1. Connect Repository → выбери `content-bot`
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `python3 bot.py`

**Environment Variables** — добавляешь все переменные из `.env.example`:

```
BOT_TOKEN             = токен из BotFather (Шаг 2)
DATABASE_URL          = External URL из Render PostgreSQL (Шаг 2)
GOOGLE_VISION_API_KEY = ключ из Google Cloud (Шаг 2)
LIBRARY_CHANNEL_ID    = ID приватного канала
GROQ_API_KEY          = ключ из console.groq.com (бесплатно)
WEBSHARE_PROXY_URL    = rotating endpoint из webshare.io (бесплатный тир)
```

**Deploy** → ждешь зеленый статус.

Проверка: зайди в Telegram → кинь боту TikTok-ссылку → должен ответить `✅ Сохранено #1`

Если застрял — скриншот в Claude Code.

---

## Что дальше

Модуль 2: выбрать платформу → бот генерирует скрипт.
Модуль 3: одобрить → опубликовать.
Следи за каналом [@headlessaimode](https://t.me/headlessaimode) — буду выкладывать по мере постройки.
