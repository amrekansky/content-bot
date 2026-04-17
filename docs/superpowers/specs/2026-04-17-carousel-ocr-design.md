# Carousel OCR Design

_Date: 2026-04-17_

## Goal

Extract text from TikTok and Instagram carousel posts (image slides with infographics). Return structured text with [Слайд N] markers per slide.

---

## Problem

Carousel posts contain images, not audio. The current pipeline tries yt-dlp subtitle extraction and Groq Whisper audio transcription — both return nothing for image-only posts. Google Vision API is already connected for handling uploaded photos, but is not used for URL-based carousel content.

Additionally, TikTok photo posts arrive as short `vt.tiktok.com` URLs indistinguishable from video URLs until download time.

---

## Solution

Add one new function `_extract_carousel_text(url: str) -> str | None` to `content_bot/services/content_processor.py`.

The function:
1. Downloads all images from the post using yt-dlp with `--proxy` (same proxy as audio downloads)
2. Runs Google Vision `document_text_detection` on each image in sorted order
3. Returns structured text: `[Слайд 1]\ntext\n\n[Слайд 2]\ntext...`
4. Returns `None` if no images downloaded or all images return empty OCR

---

## Routing in process_url()

```
YouTube URL
  → _extract_youtube_transcript()

Instagram p/ (content_type == "carousel")
  → _extract_carousel_text()   ← skip audio entirely

TikTok / Instagram reel (content_type == "video_short")
  → _extract_subtitles()
  → if None: _extract_with_groq()
  → if None: _extract_carousel_text()   ← catches TikTok photo posts with short URLs
```

The TikTok fallback works because `_download_audio` returns `None` for photo posts (no audio stream), so `_extract_with_groq` returns `None`, and execution falls through to carousel OCR naturally.

---

## yt-dlp command for image download

```bash
yt-dlp \
  --output "/tmp/carousel/%(playlist_index)s.%(ext)s" \
  [--proxy WEBSHARE_PROXY_URL] \
  <url>
```

For carousel posts, yt-dlp downloads each slide as a numbered image file (`.jpg`, `.webp`, `.png`). For single-image posts, one file is downloaded. Files are sorted by name (numeric order = slide order).

Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`

---

## Output format

```
[Слайд 1]
Заголовок инфографики
Подзаголовок
Основной текст первого слайда

[Слайд 2]
Текст второго слайда
```

Slides with empty OCR result are skipped (no `[Слайд N]` entry for blank images).

If all slides return empty OCR, function returns `None`.

---

## Files changed

- **Modify:** `content_bot/services/content_processor.py`
  - Add `_extract_carousel_text(url: str) -> str | None`
  - Update `process_url()` routing
- **Test:** `content_bot/tests/test_content_processor.py`
  - Add tests for carousel routing in `process_url()`
  - Add tests for `_extract_carousel_text()` with mocked yt-dlp and Vision API

---

## What does NOT change

- `content_bot/services/vision.py` — reused as-is
- `content_bot/handlers/content_ingest.py` — no changes, routing is inside content_processor
- Database schema — `transcript` TEXT column already handles structured text
- Archive card format — shows first 200 chars, works for any text
- `content_bot/config.py` — no new env vars needed

---

## Out of scope

- LinkedIn carousels (PDFs, different mechanism — already handled by PDF path if user uploads)
- Video + slides hybrid posts
- OCR language hints (Vision API auto-detects)
