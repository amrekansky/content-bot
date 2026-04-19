# idea-room Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a global Claude Code skill that accepts any social media URL or local file, transcribes it, generates 8 content adaptations in the author's voice, saves a комната-идей markdown file locally, and updates two Google Sheets (Library queue + Content Calendar).

**Architecture:** Three Python helper scripts (`extract_youtube.py`, `extract_audio.py`, `sheets_helper.py`) live alongside `SKILL.md` in `~/.claude/skills/idea-room/`. Claude Code reads SKILL.md and uses these scripts via Bash tool. No server, no deployment — runs entirely on the local Mac.

**Tech Stack:** python 3.11+, youtube-transcript-api, yt-dlp, mlx-whisper (Apple Silicon), gspread, python-dotenv

---

## File Map

**Create:**
- `~/.claude/skills/idea-room/SKILL.md` — skill instructions Claude follows
- `~/.claude/skills/idea-room/extract_youtube.py` — YouTube transcript via youtube-transcript-api
- `~/.claude/skills/idea-room/extract_audio.py` — yt-dlp download + mlx-whisper transcription (TikTok, Instagram, local files)
- `~/.claude/skills/idea-room/sheets_helper.py` — Library Sheets queue + Content Calendar scheduling
- `~/.claude/skills/idea-room/tests/test_extract_youtube.py`
- `~/.claude/skills/idea-room/tests/test_extract_audio.py`
- `~/.claude/skills/idea-room/tests/test_sheets_helper.py`

---

### Task 0: Setup (no code, manual steps)

**Steps:**

- [ ] **Step 1: Install Python dependencies**

```bash
pip install youtube-transcript-api yt-dlp gspread python-dotenv
pip install mlx-whisper
```

Verify:
```bash
python3 -c "from youtube_transcript_api import YouTubeTranscriptApi; print('ok')"
python3 -c "import mlx_whisper; print('ok')"
yt-dlp --version
```

- [ ] **Step 2: Create skill directory**

```bash
mkdir -p ~/.claude/skills/idea-room/tests
touch ~/.claude/skills/idea-room/tests/__init__.py
```

- [ ] **Step 3: Create Content Calendar Google Sheets**

1. Открой sheets.google.com → создай новую таблицу "Content Calendar"
2. Переименуй Sheet1 в "Calendar"
3. Добавь заголовки в строку 1 (колонки A-H):
   `Дата | Платформа | Формат | Хук | Контент | Статус | Источник URL | Файл`
4. Скопируй ID таблицы из URL: `https://docs.google.com/spreadsheets/d/**ЭТОТ_ID**/edit`
5. Добавь сервис-аккаунт (тот же что у content-bot) в шаринг таблицы: Editor

- [ ] **Step 4: Создай ~/.env с кредами**

```bash
cat >> ~/.env << 'EOF'
GOOGLE_SHEETS_CREDENTIALS=<тот же JSON что в Render env var GOOGLE_SHEETS_CREDENTIALS>
GOOGLE_SHEETS_LIBRARY_ID=<ID Library Sheets из Render env var GOOGLE_SHEETS_ID>
GOOGLE_SHEETS_CALENDAR_ID=<ID новой Content Calendar Sheets из шага 3>
EOF
```

---

### Task 1: extract_youtube.py

**Files:**
- Create: `~/.claude/skills/idea-room/extract_youtube.py`
- Test: `~/.claude/skills/idea-room/tests/test_extract_youtube.py`

- [ ] **Step 1: Write the failing test**

```python
# ~/.claude/skills/idea-room/tests/test_extract_youtube.py
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/idea-room"))

from extract_youtube import extract_transcript, parse_video_id


def test_parse_video_id_standard():
    assert parse_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_parse_video_id_short():
    assert parse_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_parse_video_id_shorts():
    assert parse_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_parse_video_id_invalid():
    assert parse_video_id("https://tiktok.com/video/123") is None

def test_extract_transcript_success():
    mock_entry = MagicMock()
    mock_entry.text = "Hello world"
    mock_list = [mock_entry]

    with patch("extract_youtube.YouTubeTranscriptApi") as MockApi:
        instance = MockApi.return_value
        instance.fetch.return_value = mock_list
        result = extract_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert result == "Hello world"

def test_extract_transcript_invalid_url():
    result = extract_transcript("https://tiktok.com/video/123")
    assert result is None

def test_extract_transcript_api_error():
    with patch("extract_youtube.YouTubeTranscriptApi") as MockApi:
        instance = MockApi.return_value
        instance.fetch.side_effect = Exception("No transcript")
        result = extract_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/.claude/skills/idea-room
python3 -m pytest tests/test_extract_youtube.py -v
```

Expected: `ImportError: No module named 'extract_youtube'`

- [ ] **Step 3: Write implementation**

```python
#!/usr/bin/env python3
# ~/.claude/skills/idea-room/extract_youtube.py
"""Extract YouTube transcript. Usage: python3 extract_youtube.py <url>"""
import re
import sys


def parse_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def extract_transcript(url: str) -> str | None:
    video_id = parse_video_id(url)
    if not video_id:
        return None
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi()
        entries = ytt.fetch(video_id, languages=["ru", "en"])
        text = " ".join(e.text for e in entries)
        return text.strip() or None
    except Exception as e:
        print(f"youtube-transcript-api failed: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_youtube.py <url>", file=sys.stderr)
        sys.exit(1)
    result = extract_transcript(sys.argv[1])
    if result:
        print(result)
    else:
        sys.exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_extract_youtube.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
cd ~/.claude/skills/idea-room
git init  # если еще нет
git add extract_youtube.py tests/test_extract_youtube.py
git commit -m "feat: add extract_youtube.py"
```

---

### Task 2: extract_audio.py

**Files:**
- Create: `~/.claude/skills/idea-room/extract_audio.py`
- Test: `~/.claude/skills/idea-room/tests/test_extract_audio.py`

- [ ] **Step 1: Write the failing test**

```python
# ~/.claude/skills/idea-room/tests/test_extract_audio.py
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/idea-room"))

from extract_audio import detect_input_type, transcribe_file


def test_detect_url_tiktok():
    assert detect_input_type("https://www.tiktok.com/video/123") == "url"

def test_detect_url_instagram():
    assert detect_input_type("https://www.instagram.com/reel/abc/") == "url"

def test_detect_local_mp4():
    assert detect_input_type("/Users/me/video.mp4") == "local"

def test_detect_local_mp3():
    assert detect_input_type("/Users/me/audio.mp3") == "local"

def test_transcribe_file_success():
    mock_result = {"text": "Hello from whisper"}
    with patch("extract_audio.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.return_value = mock_result
        result = transcribe_file("/tmp/test.mp3")
    assert result == "Hello from whisper"

def test_transcribe_file_empty():
    with patch("extract_audio.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.return_value = {"text": "  "}
        result = transcribe_file("/tmp/test.mp3")
    assert result is None

def test_transcribe_file_error():
    with patch("extract_audio.mlx_whisper") as mock_whisper:
        mock_whisper.transcribe.side_effect = Exception("model error")
        result = transcribe_file("/tmp/test.mp3")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_extract_audio.py -v
```

Expected: `ImportError: No module named 'extract_audio'`

- [ ] **Step 3: Write implementation**

```python
#!/usr/bin/env python3
# ~/.claude/skills/idea-room/extract_audio.py
"""Download audio via yt-dlp and transcribe with mlx-whisper.
Usage:
  python3 extract_audio.py <url>          # downloads, transcribes, cleans up
  python3 extract_audio.py <local_file>   # transcribes directly
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

import mlx_whisper

WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"


def detect_input_type(path: str) -> str:
    """Return 'url' for http(s) links, 'local' for file paths."""
    return "url" if path.startswith("http") else "local"


def transcribe_file(audio_path: str) -> str | None:
    """Transcribe audio file with mlx-whisper. Returns text or None."""
    try:
        result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=WHISPER_MODEL)
        text = result.get("text", "").strip()
        return text or None
    except Exception as e:
        print(f"mlx-whisper failed: {e}", file=sys.stderr)
        return None


def download_and_transcribe(url: str) -> str | None:
    """Download audio via yt-dlp into temp dir, transcribe, delete temp dir."""
    tmp_dir = tempfile.mkdtemp(prefix="idea-room-")
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "5",
                "--output", os.path.join(tmp_dir, "%(id)s.%(ext)s"),
                url,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        mp3_files = glob.glob(os.path.join(tmp_dir, "*.mp3"))
        if not mp3_files:
            print(f"yt-dlp failed (rc={result.returncode}): {result.stderr[-300:]}", file=sys.stderr)
            return None
        return transcribe_file(mp3_files[0])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_audio.py <url|filepath>", file=sys.stderr)
        sys.exit(1)

    inp = sys.argv[1]
    if detect_input_type(inp) == "url":
        text = download_and_transcribe(inp)
    else:
        text = transcribe_file(inp)

    if text:
        print(text)
    else:
        sys.exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_extract_audio.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Manual smoke test with the local mp4**

```bash
python3 ~/.claude/skills/idea-room/extract_audio.py \
  "/Users/amrekanski/ai-consultant/How I setup Claude code to have persistent memory (full guide) #claud... [7617496776748125454].mp4"
```

Expected: несколько предложений транскрипта на английском выведены в stdout. Временные файлы не остались.

- [ ] **Step 6: Commit**

```bash
git add extract_audio.py tests/test_extract_audio.py
git commit -m "feat: add extract_audio.py (yt-dlp + mlx-whisper)"
```

---

### Task 3: sheets_helper.py

**Files:**
- Create: `~/.claude/skills/idea-room/sheets_helper.py`
- Test: `~/.claude/skills/idea-room/tests/test_sheets_helper.py`

- [ ] **Step 1: Write the failing tests**

```python
# ~/.claude/skills/idea-room/tests/test_sheets_helper.py
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/idea-room"))

from sheets_helper import find_next_slot, get_taken_slots, build_calendar_rows, SCHEDULE_OFFSETS


def test_find_next_slot_empty_calendar():
    """With no taken slots, returns start_date as-is."""
    result = find_next_slot(set(), "TikTok", date(2026, 4, 20))
    assert result == date(2026, 4, 20)


def test_find_next_slot_slot_taken():
    """Pushes to next available day."""
    taken = {("2026-04-20", "TikTok"), ("2026-04-21", "TikTok")}
    result = find_next_slot(taken, "TikTok", date(2026, 4, 20))
    assert result == date(2026, 4, 22)


def test_find_next_slot_different_platform_not_blocked():
    """Slot taken by LinkedIn does not block TikTok."""
    taken = {("2026-04-20", "LinkedIn")}
    result = find_next_slot(taken, "TikTok", date(2026, 4, 20))
    assert result == date(2026, 4, 20)


def test_get_taken_slots_parses_rows():
    mock_sheet = MagicMock()
    mock_sheet.get_all_values.return_value = [
        ["Дата", "Платформа", "Формат", "Хук", "Контент", "Статус", "Источник URL", "Файл"],
        ["2026-04-20", "TikTok", "TikTok", "hook", "content", "черновик", "https://t.com", "file.md"],
        ["2026-04-21", "YouTube", "YouTube Short", "hook2", "content2", "черновик", "https://y.com", "file2.md"],
    ]
    taken = get_taken_slots(mock_sheet)
    assert ("2026-04-20", "TikTok") in taken
    assert ("2026-04-21", "YouTube") in taken
    assert len(taken) == 2


def test_get_taken_slots_skips_header_and_empty():
    mock_sheet = MagicMock()
    mock_sheet.get_all_values.return_value = [
        ["Дата", "Платформа"],
        ["", ""],
    ]
    taken = get_taken_slots(mock_sheet)
    assert len(taken) == 0


def test_build_calendar_rows_returns_8_rows():
    today = date(2026, 4, 19)
    taken = set()
    formats = {
        "tiktok": {"hook": "hook1", "content": "c1"},
        "shorts": {"hook": "hook2", "content": "c2"},
        "telegram_short": {"hook": "hook3", "content": "c3"},
        "telegram_long": {"hook": "hook4", "content": "c4"},
        "linkedin_short": {"hook": "hook5", "content": "c5"},
        "linkedin_long": {"hook": "hook6", "content": "c6"},
        "youtube_short": {"hook": "hook7", "content": "c7"},
        "youtube_long": {"hook": "hook8", "content": "c8"},
    }
    rows = build_calendar_rows(formats, "https://src.com", "file.md", today, taken)
    assert len(rows) == 8


def test_build_calendar_rows_tiktok_offset():
    today = date(2026, 4, 19)
    taken = set()
    formats = {k: {"hook": "h", "content": "c"} for k in SCHEDULE_OFFSETS}
    rows = build_calendar_rows(formats, "https://src.com", "file.md", today, taken)
    tiktok_row = next(r for r in rows if r[1] == "TikTok")
    assert tiktok_row[0] == "2026-04-20"  # today + 1


def test_build_calendar_rows_conflict_pushes_date():
    today = date(2026, 4, 19)
    taken = {("2026-04-20", "TikTok")}
    formats = {k: {"hook": "h", "content": "c"} for k in SCHEDULE_OFFSETS}
    rows = build_calendar_rows(formats, "https://src.com", "file.md", today, taken)
    tiktok_row = next(r for r in rows if r[1] == "TikTok")
    assert tiktok_row[0] == "2026-04-21"  # pushed by 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_sheets_helper.py -v
```

Expected: `ImportError: No module named 'sheets_helper'`

- [ ] **Step 3: Write implementation**

```python
#!/usr/bin/env python3
# ~/.claude/skills/idea-room/sheets_helper.py
"""Google Sheets helper for idea-room skill.

Commands:
  queue                          print JSON list of unprocessed Library rows
  mark_done <row_num>            mark Library row as обработано
  mark_error <row_num>           mark Library row as ошибка транскрипции
  add_calendar                   read JSON from stdin, write to Content Calendar
"""
import json
import os
import sys
from datetime import date, timedelta

import gspread
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.env"))

LIBRARY_ID = os.environ.get("GOOGLE_SHEETS_LIBRARY_ID")
CALENDAR_ID = os.environ.get("GOOGLE_SHEETS_CALENDAR_ID")
CREDENTIALS = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")

SCHEDULE_OFFSETS = {
    "tiktok": 1,
    "shorts": 2,
    "telegram_short": 2,
    "telegram_long": 3,
    "linkedin_short": 4,
    "linkedin_long": 5,
    "youtube_short": 7,
    "youtube_long": 14,
}

PLATFORM_LABELS = {
    "tiktok": ("TikTok", "TikTok"),
    "shorts": ("YouTube", "Shorts"),
    "telegram_short": ("Telegram", "Telegram Short"),
    "telegram_long": ("Telegram", "Telegram Long"),
    "linkedin_short": ("LinkedIn", "LinkedIn Short"),
    "linkedin_long": ("LinkedIn", "LinkedIn Long"),
    "youtube_short": ("YouTube", "YouTube Short"),
    "youtube_long": ("YouTube", "YouTube Long"),
}

CALENDAR_HEADERS = [
    "Дата", "Платформа", "Формат", "Хук",
    "Контент", "Статус", "Источник URL", "Файл",
]


def _get_client():
    creds = json.loads(CREDENTIALS)
    return gspread.service_account_from_dict(creds)


def find_next_slot(taken: set, platform: str, start: date) -> date:
    """Return nearest date >= start where platform has no entry."""
    d = start
    while (d.strftime("%Y-%m-%d"), platform) in taken:
        d += timedelta(days=1)
    return d


def get_taken_slots(sheet) -> set:
    """Return set of (date_str, platform) tuples from calendar sheet."""
    rows = sheet.get_all_values()
    taken = set()
    for row in rows[1:]:
        if len(row) >= 2 and row[0] and row[1]:
            taken.add((row[0], row[1]))
    return taken


def build_calendar_rows(
    formats: dict,
    source_url: str,
    file_path: str,
    today: date,
    taken: set,
) -> list[list]:
    """Build 8 Sheets rows for Content Calendar, auto-scheduling dates."""
    rows = []
    for key, offset in SCHEDULE_OFFSETS.items():
        if key not in formats:
            continue
        platform, fmt_label = PLATFORM_LABELS[key]
        start = today + timedelta(days=offset)
        slot = find_next_slot(taken, platform, start)
        taken.add((slot.strftime("%Y-%m-%d"), platform))
        rows.append([
            slot.strftime("%Y-%m-%d"),
            platform,
            fmt_label,
            formats[key]["hook"],
            formats[key]["content"],
            "черновик",
            source_url,
            file_path,
        ])
    return rows


def cmd_queue():
    client = _get_client()
    sheet = client.open_by_key(LIBRARY_ID).sheet1
    all_rows = sheet.get_all_values()
    result = []
    for i, row in enumerate(all_rows[1:], start=2):
        if len(row) >= 8 and row[7].strip() in ("новый", ""):
            result.append({"row_num": i, "url": row[1], "platform": row[2]})
    print(json.dumps(result, ensure_ascii=False))


def cmd_mark_done(row_num: int):
    client = _get_client()
    sheet = client.open_by_key(LIBRARY_ID).sheet1
    sheet.update_cell(row_num, 8, "обработано")
    print("OK")


def cmd_mark_error(row_num: int):
    client = _get_client()
    sheet = client.open_by_key(LIBRARY_ID).sheet1
    sheet.update_cell(row_num, 8, "ошибка транскрипции")
    print("OK")


def cmd_add_calendar():
    data = json.loads(sys.stdin.read())
    client = _get_client()
    sheet = client.open_by_key(CALENDAR_ID).sheet1

    # Ensure header row
    first_row = sheet.row_values(1)
    if not first_row or first_row[0] != "Дата":
        sheet.update("A1", [CALENDAR_HEADERS])

    taken = get_taken_slots(sheet)
    today = date.today()
    rows = build_calendar_rows(
        data["formats"],
        data["source_url"],
        data["file_path"],
        today,
        taken,
    )

    # Append after last data row
    col_a = sheet.col_values(1)
    last_row = max((i + 1 for i, v in enumerate(col_a) if v and v.strip()), default=1)
    sheet.update(f"A{last_row + 1}", rows)

    dates = [r[0] for r in rows]
    print(json.dumps({"added": len(rows), "dates": dates}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "queue":
        cmd_queue()
    elif cmd == "mark_done":
        cmd_mark_done(int(sys.argv[2]))
    elif cmd == "mark_error":
        cmd_mark_error(int(sys.argv[2]))
    elif cmd == "add_calendar":
        cmd_add_calendar()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_sheets_helper.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add sheets_helper.py tests/test_sheets_helper.py
git commit -m "feat: add sheets_helper.py (queue + scheduling + calendar)"
```

---

### Task 4: SKILL.md

**Files:**
- Create: `~/.claude/skills/idea-room/SKILL.md`

No unit tests — verification is manual (run the skill).

- [ ] **Step 1: Create SKILL.md**

```markdown
# idea-room

Обрабатывает контент из соцсетей: транскрибирует, анализирует, генерирует 8 адаптаций в голосе автора, сохраняет markdown в комната-идей/, обновляет Google Sheets.

## Использование

```
idea-room                    # очередь: читает Library Sheets, обрабатывает все новые
idea-room <url>              # один URL напрямую
idea-room <filepath>         # локальный файл (.mp4 .mp3 .jpg .png .pdf)
```

---

## ШАГ 1: Определить режим и входные данные

Посмотри на аргументы которые тебе передали:
- Нет аргументов → **queue mode**: получи список URL из Library Sheets и обработай каждый
- Аргумент начинается с `http` → **URL mode**: обработай этот URL
- Аргумент — путь к файлу → **file mode**: обработай локальный файл

**В queue mode** выполни:
```bash
python3 ~/.claude/skills/idea-room/sheets_helper.py queue
```
Получишь JSON: `[{"row_num": 2, "url": "https://...", "platform": "tiktok"}, ...]`
Обработай каждый элемент последовательно как URL mode. После каждого — обнови статус в Sheets (Шаг 6).
Если список пустой — выведи "Нет новых записей в очереди" и заверши.

---

## ШАГ 2: Определить тип входа и извлечь транскрипт

Определи тип по URL или расширению файла:

**YouTube** (содержит `youtube.com` или `youtu.be`):
```bash
python3 ~/.claude/skills/idea-room/extract_youtube.py "<url>"
```
Если скрипт завершился с ошибкой (exit code != 0) → fallback на extract_audio.py.

**TikTok** (содержит `tiktok.com`) или **Instagram** (содержит `instagram.com`):
```bash
python3 ~/.claude/skills/idea-room/extract_audio.py "<url>"
```

**Вебсайт / статья** (любой другой http URL без медиа-расширения):
Используй WebFetch tool для получения текста страницы. Этот текст — транскрипт.

**Картинка** (расширение `.jpg` `.jpeg` `.png` `.webp` `.gif`, или URL с таким расширением):
Используй Read tool — ты видишь изображения нативно. Весь текст который видишь на изображении — транскрипт.

**PDF** (расширение `.pdf`):
Используй Read tool — нативная поддержка PDF. Текст документа — транскрипт.

**Локальный видео/аудио** (расширение `.mp4` `.mp3` `.mov` `.m4a` `.wav` `.avi`):
```bash
python3 ~/.claude/skills/idea-room/extract_audio.py "<filepath>"
```

Если транскрипт не получен:
- В queue mode: выполни `python3 ~/.claude/skills/idea-room/sheets_helper.py mark_error <row_num>`, переходи к следующей записи
- В URL/file mode: сообщи об ошибке и заверши

---

## ШАГ 3: Загрузить голос автора

Прочитай все четыре файла с помощью Read tool:
1. `/Users/amrekanski/ai-consultant/04-sales/linkedin-about-ru.md`
2. `/Users/amrekanski/ai-consultant/04-sales/telegram-channel/post-kto-ya.md`
3. `/Users/amrekanski/ai-consultant/04-sales/telegram-channel/post-what-is-headless.md`
4. `/Users/amrekanski/ai-consultant/04-sales/telegram-channel/post-content-bot.md`

---

## ШАГ 4: Анализ и генерация

Используя транскрипт из Шага 2 и голос автора из Шага 3, напиши следующее.
Стиль: прямой, без воды, личные истории с конкретными деталями, технические термины без объяснений, антихайп, разговорный.

**АНАЛИЗ ОРИГИНАЛА**
Хук: первые 1-2 предложения / первые 3-5 секунд оригинала
Структура: как построен контент, 1-2 предложения
CTA: что просят сделать в конце
Тон: стиль автора, 1 предложение
Главная идея: одна идея которую можно адаптировать (одно предложение)

**АДАПТАЦИИ** — пиши строго в голосе автора на основе примеров из Шага 3:

YouTube длинный (2-3 мин): разговорный скрипт с личной историей, конкретные детали, развернутое объяснение, CTA в конце
YouTube короткий (60s): сильный хук в первую секунду, один главный тезис, быстрый темп
TikTok (30-45s): максимально быстрый темп, визуальные хуки, прямо к делу без предисловий
Shorts (30-45s): хук в первые 3 секунды, один месседж, вертикальный формат
LinkedIn длинный (3-5 абзацев): начало с провокационного тезиса или личной истории, конкретные примеры, профессиональный инсайт, без корпоративного языка
LinkedIn короткий (2-3 абзаца): прямо к делу, без разгона
Telegram длинный: полный пост со структурой, подзаголовки если нужно, CTA в конце
Telegram короткий: 3-5 предложений, удар без предисловий

**ЗАМЕТКИ**
Что сработало в оригинале: 2-3 конкретных техники
Идеи для контента: 2-3 идеи как использовать отдельно

---

## ШАГ 5: Определить slug и сохранить markdown

Slug: первые 4-5 значимых слов из "Главная идея", только строчные латинские буквы и цифры через дефис. Если слова русские — транслитерируй.
Дата: сегодняшняя в формате YYYY-MM-DD.
Путь файла: `/Users/amrekanski/ai-consultant/комната-идей/<YYYY-MM-DD>_<slug>.md`

Запомни этот путь — он понадобится в Шаге 7.

Сохрани файл с Write tool в следующем формате:

```
# <Главная идея>

**Источник:** <url или filepath>
**Дата:** <YYYY-MM-DD>
**Метод транскрипции:** <youtube-api / whisper / vision / webfetch>
**Язык оригинала:** <EN / RU>

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

---

## ШАГ 6: Обновить Library Sheets (только для queue mode)

```bash
python3 ~/.claude/skills/idea-room/sheets_helper.py mark_done <row_num>
```

---

## ШАГ 7: Добавить в Content Calendar

Подготовь JSON со всеми 8 форматами. Для каждого формата: hook = первое предложение адаптации, content = полный текст.

Передай в sheets_helper через stdin:

```bash
python3 ~/.claude/skills/idea-room/sheets_helper.py add_calendar << 'ENDJSON'
{
  "source_url": "<url или filepath>",
  "file_path": "<путь к markdown файлу из Шага 5>",
  "formats": {
    "tiktok":          {"hook": "<первое предложение TikTok>", "content": "<полный текст TikTok>"},
    "shorts":          {"hook": "<первое предложение Shorts>", "content": "<полный текст Shorts>"},
    "telegram_short":  {"hook": "<первое предложение TG Short>", "content": "<полный текст TG Short>"},
    "telegram_long":   {"hook": "<первое предложение TG Long>", "content": "<полный текст TG Long>"},
    "linkedin_short":  {"hook": "<первое предложение LI Short>", "content": "<полный текст LI Short>"},
    "linkedin_long":   {"hook": "<первое предложение LI Long>", "content": "<полный текст LI Long>"},
    "youtube_short":   {"hook": "<первое предложение YT Short>", "content": "<полный текст YT Short>"},
    "youtube_long":    {"hook": "<первое предложение YT Long>", "content": "<полный текст YT Long>"}
  }
}
ENDJSON
```

---

## ШАГ 8: Итог

Выведи сводку:

```
✅ Файл: /Users/amrekanski/ai-consultant/комната-идей/2026-04-20_slug.md
✅ Library Sheets: обновлено (row N)
✅ Content Calendar: добавлено 8 записей
   TikTok         → 2026-04-20
   Shorts         → 2026-04-21
   Telegram Short → 2026-04-21
   Telegram Long  → 2026-04-22
   LinkedIn Short → 2026-04-23
   LinkedIn Long  → 2026-04-24
   YouTube Short  → 2026-04-27
   YouTube Long   → 2026-05-03
```

В queue mode: после каждой записи выводи прогресс `[1/3] Обработано: https://...`, в конце итог по всей очереди.
```

- [ ] **Step 2: Verify skill is accessible**

```bash
ls ~/.claude/skills/idea-room/
```

Expected:
```
SKILL.md  extract_audio.py  extract_youtube.py  sheets_helper.py  tests/
```

- [ ] **Step 3: Smoke test — локальный mp4**

В Claude Code сессии запусти:
```
idea-room "/Users/amrekanski/ai-consultant/How I setup Claude code to have persistent memory (full guide) #claud... [7617496776748125454].mp4"
```

Expected:
- Claude читает SKILL.md
- Запускает extract_audio.py на файле
- Получает транскрипт
- Читает 4 голосовых файла
- Генерирует анализ + 8 адаптаций
- Сохраняет markdown в комната-идей/
- Выводит итог с датами

- [ ] **Step 4: Smoke test — YouTube URL**

```
idea-room https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Expected: аналогично, метод транскрипции = `youtube-api`

- [ ] **Step 5: Commit**

```bash
git add SKILL.md
git commit -m "feat: add idea-room SKILL.md"
```

---

### Task 5: Module 1 integration smoke test

Проверить что queue mode корректно читает реальные данные из Library Sheets.

- [ ] **Step 1: Добавь тестовую ссылку в бота**

Отправь YouTube URL боту в Telegram. Бот должен сохранить запись со статусом "новый" в Library Sheets.

- [ ] **Step 2: Запусти queue mode**

```
idea-room
```

Expected:
- `python3 sheets_helper.py queue` возвращает JSON с 1 записью
- Claude обрабатывает URL
- После обработки `sheets_helper.py mark_done <row_num>` меняет статус на "обработано"
- В Content Calendar появились 8 новых строк с расписанием
- В комната-идей/ появился новый .md файл

- [ ] **Step 3: Проверь что повторный запуск пропускает обработанные**

```
idea-room
```

Expected: `Нет новых записей в очереди`
