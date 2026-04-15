# Как я запилил Content Bot с нуля в Claude Code

> Это живая документация — пишется параллельно с кодом.
> Каждый шаг: что делаю, почему, какие команды запускаю.

---

## Что строим

Бот принимает ссылки (TikTok, YouTube, Reels, LinkedIn) и медиафайлы.
Транскрибирует, сохраняет в базу, форвардит в приватный архив-канал.
Дальше — генерирует контент под твой голос (Модуль 2, отдельно).

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

<!-- ЗАПОЛНЯЕТСЯ В TASK 3 -->

---

## Шаг 4.3 — services/content_processor.py: yt-dlp

<!-- ЗАПОЛНЯЕТСЯ В TASK 4 -->

---

## Шаг 4.4 — handlers/content_ingest.py: входящие сообщения

<!-- ЗАПОЛНЯЕТСЯ В TASK 5 -->

---

## Шаг 4.5 — bot.py: сборка и запуск

<!-- ЗАПОЛНЯЕТСЯ В TASK 6 -->

---

## Шаг 5 — Деплой на Render

<!-- ЗАПОЛНЯЕТСЯ В TASK 6 -->

---

## Что дальше

Модуль 2: выбрать платформу → бот генерирует скрипт.
Модуль 3: одобрить → опубликовать.
Следи за каналом [@headlessaimode](https://t.me/headlessaimode) — буду выкладывать по мере постройки.
