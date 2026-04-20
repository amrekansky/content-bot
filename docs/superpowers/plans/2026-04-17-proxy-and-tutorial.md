# Proxy Fix + Tutorial Storytelling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route yt-dlp through a residential proxy to fix transcript extraction on Render, and update TUTORIAL.md with the full debugging story.

**Architecture:** Two independent tasks. Task 1 adds an optional `WEBSHARE_PROXY_URL` env var that is injected as `--proxy` into both yt-dlp subprocess calls. Task 2 updates TUTORIAL.md: fixes the Render deploy step (Web Service → Background Worker, missing env vars) and adds a storytelling section about the debugging journey.

**Tech Stack:** Python 3.11, yt-dlp (subprocess), python-dotenv, Webshare rotating residential proxy

---

## File Map

**Modify:**
- `content_bot/config.py` — add optional `WEBSHARE_PROXY_URL`
- `content_bot/services/content_processor.py` — inject `--proxy` into `_extract_subtitles` and `_download_audio`
- `.env.example` — add `WEBSHARE_PROXY_URL` with comment
- `TUTORIAL.md` — fix Шаг 5 + add storytelling section

**Test:**
- `content_bot/tests/test_content_processor.py` — add proxy behavior tests

---

## Task 1: Add Webshare proxy support to yt-dlp calls

**Files:**
- Modify: `content_bot/config.py`
- Modify: `content_bot/services/content_processor.py`
- Modify: `.env.example`
- Test: `content_bot/tests/test_content_processor.py`

- [ ] **Step 1: Write two failing tests for proxy behavior**

Add to `content_bot/tests/test_content_processor.py`:

```python
def test_extract_subtitles_passes_proxy_when_set():
    """When WEBSHARE_PROXY_URL is set, --proxy flag appears in yt-dlp command."""
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\n"

    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("builtins.open", mock_open(read_data=vtt_content)), \
         patch("content_bot.services.content_processor.os.remove"), \
         patch("content_bot.config.WEBSHARE_PROXY_URL", "http://user:pass@p.webshare.io:80"):

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.side_effect = [["/tmp/abc.vtt"], []]

        process_url("https://www.tiktok.com/@user/video/123")

        cmd = mock_run.call_args[0][0]
        assert "--proxy" in cmd
        assert "http://user:pass@p.webshare.io:80" in cmd


def test_extract_subtitles_no_proxy_when_not_set():
    """When WEBSHARE_PROXY_URL is not set, --proxy is absent from yt-dlp command."""
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\n"

    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("builtins.open", mock_open(read_data=vtt_content)), \
         patch("content_bot.services.content_processor.os.remove"), \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.side_effect = [["/tmp/abc.vtt"], []]

        process_url("https://www.tiktok.com/@user/video/123")

        cmd = mock_run.call_args[0][0]
        assert "--proxy" not in cmd
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /path/to/content-bot
pytest content_bot/tests/test_content_processor.py::test_extract_subtitles_passes_proxy_when_set content_bot/tests/test_content_processor.py::test_extract_subtitles_no_proxy_when_not_set -v
```

Expected: FAIL — `AssertionError: assert '--proxy' in [...]`

- [ ] **Step 3: Add WEBSHARE_PROXY_URL to config.py**

Current `content_bot/config.py` ends with:
```python
GROQ_API_KEY: str | None = os.environ.get("GROQ_API_KEY")
```

Add one line after it:
```python
WEBSHARE_PROXY_URL: str | None = os.environ.get("WEBSHARE_PROXY_URL")
```

Full file after edit:
```python
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required env var {key!r} is not set")
    return val


def _require_int(key: str) -> int:
    val = _require(key)
    try:
        return int(val)
    except ValueError:
        raise ValueError(f"Env var {key!r} must be an integer, got {val!r}")


BOT_TOKEN: str = _require("BOT_TOKEN")
DATABASE_URL: str = _require("DATABASE_URL")
GOOGLE_VISION_API_KEY: str = _require("GOOGLE_VISION_API_KEY")
LIBRARY_CHANNEL_ID: int = _require_int("LIBRARY_CHANNEL_ID")
GROQ_API_KEY: str | None = os.environ.get("GROQ_API_KEY")
WEBSHARE_PROXY_URL: str | None = os.environ.get("WEBSHARE_PROXY_URL")
```

- [ ] **Step 4: Inject proxy into _extract_subtitles and _download_audio**

In `content_bot/services/content_processor.py`, replace `_extract_subtitles`:

```python
def _extract_subtitles(url: str, tmp_dir: str) -> str | None:
    """Run yt-dlp to extract subtitles. Return clean text or None."""
    from content_bot.config import WEBSHARE_PROXY_URL
    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "ru,en",
        "--skip-download",
        "--output", os.path.join(tmp_dir, "%(id)s"),
    ]
    if WEBSHARE_PROXY_URL:
        cmd += ["--proxy", WEBSHARE_PROXY_URL]
    cmd.append(url)
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    vtt_files = glob.glob(os.path.join(tmp_dir, "*.vtt"))
    if not vtt_files:
        vtt_files = glob.glob(os.path.join(tmp_dir, "*.srt"))

    if not vtt_files:
        return None

    try:
        with open(vtt_files[0], "r", encoding="utf-8") as f:
            raw = f.read()
        text = parse_vtt_text(raw)
        return text if text.strip() else None
    finally:
        for f in vtt_files:
            try:
                os.remove(f)
            except OSError:
                pass
```

Replace `_download_audio`:

```python
def _download_audio(url: str, tmp_dir: str) -> str | None:
    """Download audio as mp3 via yt-dlp. Returns file path or None."""
    from content_bot.config import WEBSHARE_PROXY_URL
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",  # ~64kbps mono, keeps file under 25MB
        "--output", os.path.join(tmp_dir, "%(id)s.%(ext)s"),
    ]
    if WEBSHARE_PROXY_URL:
        cmd += ["--proxy", WEBSHARE_PROXY_URL]
    cmd.append(url)
    subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    mp3_files = glob.glob(os.path.join(tmp_dir, "*.mp3"))
    return mp3_files[0] if mp3_files else None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest content_bot/tests/test_content_processor.py -v
```

Expected: All tests PASS, including the two new proxy tests.

- [ ] **Step 6: Update .env.example**

Current `.env.example`:
```
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql://user:pass@host.render.com/dbname
GOOGLE_VISION_API_KEY=your_google_vision_api_key_here
LIBRARY_CHANNEL_ID=-100xxxxxxxxxx
```

Replace with:
```
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql://user:pass@host.render.com/dbname
GOOGLE_VISION_API_KEY=your_google_vision_api_key_here
LIBRARY_CHANNEL_ID=-100xxxxxxxxxx
GROQ_API_KEY=your_groq_api_key_here
# Get from webshare.io → Proxy List → rotating endpoint
# Format: http://<user>-rotate:<password>@p.webshare.io:80
WEBSHARE_PROXY_URL=
```

- [ ] **Step 7: Commit**

```bash
git add content_bot/config.py content_bot/services/content_processor.py .env.example content_bot/tests/test_content_processor.py
git commit -m "feat: route yt-dlp through residential proxy via WEBSHARE_PROXY_URL"
```

- [ ] **Step 8: Push and set env var on Render**

```bash
git push origin main
```

Then on Render → Environment → add:
```
WEBSHARE_PROXY_URL = http://<user>-rotate:<password>@p.webshare.io:80
```

(Get this URL from webshare.io → Dashboard → Proxy List → Rotating Endpoint after registering a free account.)

---

## Task 2: Update TUTORIAL.md with fixes and storytelling

**Files:**
- Modify: `TUTORIAL.md`

No unit tests for documentation. Verify by reading the file after edits.

- [ ] **Step 1: Fix Шаг 5 — Web Service → Background Worker**

In `TUTORIAL.md`, find this block in Шаг 5:

```
**render.com → New → Web Service**

1. Connect Repository → выбери `content-bot`
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `python3 bot.py`

**Environment Variables** — добавляешь все переменные из `.env.example`:

```
BOT_TOKEN          = токен из BotFather (Шаг 2)
DATABASE_URL       = External URL из Render PostgreSQL (Шаг 2)
GOOGLE_VISION_API_KEY = ключ из Google Cloud (Шаг 2)
LIBRARY_CHANNEL_ID = ID приватного канала
```
```

Replace with:

```
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
```

- [ ] **Step 2: Update Шаг 4.3 — reflect full transcript extraction chain**

Find in `TUTORIAL.md` the Шаг 4.3 section. Replace the paragraph starting "yt-dlp скачивает субтитры":

```
Никакого LLM на этом этапе. Бот — механический сборщик.
yt-dlp скачивает субтитры (не аудио, только `.vtt` файл), функция чистит таймкоды.
```

Replace with:

```
Никакого LLM на этом этапе. Бот — механический сборщик.
Транскрипт извлекается в три попытки:

1. **youtube-transcript-api** — самый быстрый путь для YouTube, без скачивания
2. **Groq Whisper** — скачивает аудио через yt-dlp (mp3, ~64kbps), отправляет в Whisper API
3. **yt-dlp субтитры** — последний резерв, `.vtt` файл без аудио

Для TikTok и Instagram: сначала субтитры через yt-dlp, потом Groq Whisper.
Все yt-dlp вызовы идут через residential proxy (WEBSHARE_PROXY_URL) —
без этого Render'овский datacenter IP блокируется YouTube и TikTok.
```

- [ ] **Step 3: Add storytelling section after Шаг 4.5**

After the `## Шаг 4.5 — bot.py: сборка и запуск` section (before `## Шаг 5 — Деплой на Render`), add:

```markdown
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
```

- [ ] **Step 4: Verify the file looks right**

```bash
grep -n "Background Worker\|WEBSHARE_PROXY_URL\|три фикса\|Фикс 1" TUTORIAL.md
```

Expected output: lines found for each grep term — confirms all edits landed.

- [ ] **Step 5: Commit**

```bash
git add TUTORIAL.md
git commit -m "docs: fix Render deploy step + add transcript debugging story to TUTORIAL"
```

- [ ] **Step 6: Push**

```bash
git push origin main
```
