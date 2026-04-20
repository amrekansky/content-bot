# Carousel OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `_extract_carousel_text()` to extract text from TikTok/Instagram image carousels using yt-dlp + Google Vision OCR, and wire it into `process_url()` routing.

**Architecture:** One new function in `content_processor.py` downloads carousel images via yt-dlp (with proxy), runs Vision API OCR on each, returns `[Слайд N]`-structured text. `process_url()` routes Instagram `p/` directly to carousel OCR; TikTok falls back to carousel OCR when audio extraction returns nothing (photo posts have no audio stream).

**Tech Stack:** yt-dlp, Google Cloud Vision API, subprocess, tempfile, glob

---

## File Map

**Modify only:**
- `content_bot/services/content_processor.py` — add `_extract_carousel_text()`, update `process_url()`
- `content_bot/tests/test_content_processor.py` — add carousel tests

---

## Task 1: Add `_extract_carousel_text()` with tests

**Files:**
- Modify: `content_bot/services/content_processor.py`
- Test: `content_bot/tests/test_content_processor.py`

- [ ] **Step 1: Write the failing test for structured slide output**

Add to `content_bot/tests/test_content_processor.py` (add `_extract_carousel_text` to imports from `content_bot.services.content_processor`):

```python
from content_bot.services.content_processor import (
    detect_url_type,
    parse_vtt_text,
    process_url,
    ProcessedContent,
    _extract_carousel_text,
)
```

Then add the test:

```python
def test_extract_carousel_text_structures_slides():
    """Multiple downloaded images produce [Слайд N] markers in order."""
    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("content_bot.services.vision.extract_text_from_image") as mock_ocr, \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=0)
        # glob is called 4 times (jpg, jpeg, png, webp) — first call returns 2 images
        mock_glob.side_effect = [
            ["/tmp/fake/1.jpg", "/tmp/fake/2.jpg"],
            [],
            [],
            [],
        ]
        mock_ocr.side_effect = ["Текст первого слайда", "Текст второго слайда"]

        result = _extract_carousel_text("https://www.instagram.com/p/abc123/")

    assert result is not None
    assert "[Слайд 1]\nТекст первого слайда" in result
    assert "[Слайд 2]\nТекст второго слайда" in result
```

- [ ] **Step 2: Write the failing test for no images → None**

```python
def test_extract_carousel_text_returns_none_when_no_images():
    """Returns None if yt-dlp downloads nothing."""
    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=1)
        mock_glob.return_value = []

        result = _extract_carousel_text("https://www.instagram.com/p/abc123/")

    assert result is None
```

- [ ] **Step 3: Write the failing test for blank OCR → None**

```python
def test_extract_carousel_text_returns_none_when_all_ocr_empty():
    """Returns None if all images have no text."""
    with patch("content_bot.services.content_processor.subprocess.run") as mock_run, \
         patch("content_bot.services.content_processor.glob.glob") as mock_glob, \
         patch("content_bot.services.vision.extract_text_from_image") as mock_ocr, \
         patch("content_bot.config.WEBSHARE_PROXY_URL", None):

        mock_run.return_value = MagicMock(returncode=0)
        mock_glob.side_effect = [["/tmp/fake/1.jpg"], [], [], []]
        mock_ocr.return_value = ""  # Vision API returns nothing

        result = _extract_carousel_text("https://www.instagram.com/p/abc123/")

    assert result is None
```

- [ ] **Step 4: Run tests to verify they all fail**

```bash
cd /path/to/content-bot
pytest content_bot/tests/test_content_processor.py::test_extract_carousel_text_structures_slides content_bot/tests/test_content_processor.py::test_extract_carousel_text_returns_none_when_no_images content_bot/tests/test_content_processor.py::test_extract_carousel_text_returns_none_when_all_ocr_empty -v
```

Expected: FAIL — `ImportError: cannot import name '_extract_carousel_text'`

- [ ] **Step 5: Implement `_extract_carousel_text()`**

Add this function to `content_bot/services/content_processor.py`, after `_extract_with_groq` (around line 169, before `process_url`):

```python
def _extract_carousel_text(url: str) -> str | None:
    """Download carousel images via yt-dlp and OCR each with Google Vision."""
    from content_bot.config import WEBSHARE_PROXY_URL
    from content_bot.services import vision

    with tempfile.TemporaryDirectory() as tmp_dir:
        cmd = [
            "yt-dlp",
            "--output", os.path.join(tmp_dir, "%(playlist_index)s.%(ext)s"),
        ]
        if WEBSHARE_PROXY_URL:
            cmd += ["--proxy", WEBSHARE_PROXY_URL]
        cmd.append(url)
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        image_files = []
        for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            image_files.extend(glob.glob(os.path.join(tmp_dir, pattern)))
        image_files = sorted(image_files)

        if not image_files:
            logger.info("carousel: no images downloaded for %s", url)
            return None

        slides = []
        for i, image_path in enumerate(image_files, 1):
            try:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                text = vision.extract_text_from_image(image_bytes)
                if text.strip():
                    slides.append(f"[Слайд {i}]\n{text.strip()}")
            except Exception as e:
                logger.info("carousel: OCR failed for slide %d (%s)", i, e)

        return "\n\n".join(slides) if slides else None
```

**Note on mocking:** The function uses `vision.extract_text_from_image` via a module reference (`from content_bot.services import vision`). Tests must patch `content_bot.services.vision.extract_text_from_image` — not `content_bot.services.content_processor.vision.extract_text_from_image`.

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest content_bot/tests/test_content_processor.py::test_extract_carousel_text_structures_slides content_bot/tests/test_content_processor.py::test_extract_carousel_text_returns_none_when_no_images content_bot/tests/test_content_processor.py::test_extract_carousel_text_returns_none_when_all_ocr_empty -v
```

Expected: All 3 PASS.

- [ ] **Step 7: Run full test suite to verify no regressions**

```bash
pytest content_bot/tests/test_content_processor.py -v
```

Expected: All existing tests still PASS.

- [ ] **Step 8: Commit**

```bash
git add content_bot/services/content_processor.py content_bot/tests/test_content_processor.py
git commit -m "feat: add _extract_carousel_text — yt-dlp image download + Vision OCR"
```

---

## Task 2: Wire carousel routing into `process_url()`

**Files:**
- Modify: `content_bot/services/content_processor.py` (lines 171–193)
- Test: `content_bot/tests/test_content_processor.py`

- [ ] **Step 1: Write the failing test — Instagram carousel routes to OCR, not audio**

```python
def test_process_url_instagram_carousel_routes_to_ocr():
    """Instagram p/ (carousel) goes to _extract_carousel_text, skips audio pipeline."""
    with patch("content_bot.services.content_processor._extract_carousel_text") as mock_carousel, \
         patch("content_bot.services.content_processor._extract_subtitles") as mock_subs, \
         patch("content_bot.services.content_processor._extract_with_groq") as mock_groq:

        mock_carousel.return_value = "[Слайд 1]\nИнфографика"

        result = process_url("https://www.instagram.com/p/abc123/")

    mock_carousel.assert_called_once_with("https://www.instagram.com/p/abc123/")
    mock_subs.assert_not_called()
    mock_groq.assert_not_called()
    assert result.platform == "instagram"
    assert result.content_type == "carousel"
    assert result.transcript == "[Слайд 1]\nИнфографика"
```

- [ ] **Step 2: Write the failing test — TikTok falls back to carousel when audio fails**

```python
def test_process_url_tiktok_falls_back_to_carousel_when_no_audio():
    """TikTok with no audio/subtitles tries _extract_carousel_text as final fallback."""
    with patch("content_bot.services.content_processor._extract_subtitles") as mock_subs, \
         patch("content_bot.services.content_processor._extract_with_groq") as mock_groq, \
         patch("content_bot.services.content_processor._extract_carousel_text") as mock_carousel:

        mock_subs.return_value = None   # no subtitles
        mock_groq.return_value = None   # no audio (photo post)
        mock_carousel.return_value = "[Слайд 1]\nТекст из слайда"

        result = process_url("https://www.tiktok.com/@user/video/123")

    mock_carousel.assert_called_once()
    assert result.transcript == "[Слайд 1]\nТекст из слайда"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest content_bot/tests/test_content_processor.py::test_process_url_instagram_carousel_routes_to_ocr content_bot/tests/test_content_processor.py::test_process_url_tiktok_falls_back_to_carousel_when_no_audio -v
```

Expected: FAIL — `AssertionError: mock_subs was called` (carousel branch not yet implemented)

- [ ] **Step 4: Update `process_url()` with carousel routing**

Replace the current `process_url()` body (lines 171–193) with:

```python
def process_url(url: str) -> ProcessedContent | None:
    """Process a URL: detect type, extract transcript. Returns None for unknown URLs."""
    url_info = detect_url_type(url)
    if url_info is None:
        return None

    platform = url_info["platform"]
    content_type = url_info["content_type"]

    if platform == "youtube":
        transcript = _extract_youtube_transcript(url)
    elif content_type == "carousel":
        transcript = _extract_carousel_text(url)
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            transcript = _extract_subtitles(url, tmp_dir)
        if not transcript:
            transcript = _extract_with_groq(url, platform)
        if not transcript:
            transcript = _extract_carousel_text(url)

    return ProcessedContent(
        platform=platform,
        content_type=content_type,
        transcript=transcript,
        source_url=url,
    )
```

- [ ] **Step 5: Run the two new routing tests to verify they pass**

```bash
pytest content_bot/tests/test_content_processor.py::test_process_url_instagram_carousel_routes_to_ocr content_bot/tests/test_content_processor.py::test_process_url_tiktok_falls_back_to_carousel_when_no_audio -v
```

Expected: Both PASS.

- [ ] **Step 6: Run full test suite**

```bash
pytest content_bot/tests/test_content_processor.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit and push**

```bash
git add content_bot/services/content_processor.py content_bot/tests/test_content_processor.py
git commit -m "feat: route carousel URLs to OCR pipeline in process_url()"
git push origin main
```
