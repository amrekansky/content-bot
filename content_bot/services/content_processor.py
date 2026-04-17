import glob
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessedContent:
    platform: str
    content_type: str
    transcript: str | None
    source_url: str


_URL_PATTERNS = [
    (r"tiktok\.com", "tiktok", "video_short"),
    (r"vm\.tiktok\.com", "tiktok", "video_short"),
    (r"instagram\.com/reel/", "instagram", "video_short"),
    (r"instagram\.com/p/", "instagram", "carousel"),
    (r"youtube\.com/watch", "youtube", "video"),
    (r"youtu\.be/", "youtube", "video"),
    (r"linkedin\.com", "linkedin", "post"),
]


def detect_url_type(url: str) -> dict | None:
    """Return {platform, content_type} for a known URL, or None."""
    for pattern, platform, content_type in _URL_PATTERNS:
        if re.search(pattern, url):
            return {"platform": platform, "content_type": content_type}
    return None


def parse_vtt_text(vtt_content: str) -> str:
    """Strip VTT/SRT timecodes and return clean deduplicated text."""
    lines = []
    seen = set()
    for line in vtt_content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "WEBVTT":
            continue
        if re.match(r"^\d+$", line):
            continue
        if "-->" in line:
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return " ".join(lines)


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


def _extract_youtube_transcript(url: str) -> str | None:
    """Try youtube-transcript-api → Groq Whisper → yt-dlp subtitles."""

    # 1. youtube-transcript-api (fastest, no download)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        video_id_match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
        if video_id_match:
            video_id = video_id_match.group(1)
            ytt = YouTubeTranscriptApi()
            transcript_list = ytt.fetch(video_id, languages=["ru", "en"])
            text = " ".join(entry.text for entry in transcript_list)
            if text.strip():
                logger.info("youtube-transcript-api succeeded")
                return text.strip()
    except Exception as e:
        logger.info("youtube-transcript-api failed (%s)", e)

    # 2. Groq Whisper (download audio + transcribe)
    text = _extract_with_groq(url, "youtube")
    if text:
        return text

    # 3. yt-dlp subtitles (last resort)
    with tempfile.TemporaryDirectory() as tmp_dir:
        return _extract_subtitles(url, tmp_dir)


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
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    mp3_files = glob.glob(os.path.join(tmp_dir, "*.mp3"))
    return mp3_files[0] if mp3_files else None


def _transcribe_with_groq(audio_path: str, api_key: str) -> str | None:
    """Transcribe audio file using Groq Whisper API."""
    from groq import Groq
    client = Groq(api_key=api_key)
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f),
            model="whisper-large-v3-turbo",
        )
    return transcription.text.strip() or None


def _extract_with_groq(url: str, platform: str) -> str | None:
    """Download audio and transcribe with Groq Whisper."""
    from content_bot.config import GROQ_API_KEY
    if not GROQ_API_KEY:
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = _download_audio(url, tmp_dir)
            if audio_path:
                text = _transcribe_with_groq(audio_path, GROQ_API_KEY)
                if text:
                    logger.info("Groq Whisper succeeded for %s", platform)
                    return text
    except Exception as e:
        logger.info("Groq Whisper failed for %s (%s)", platform, e)
    return None


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
        image_files = sorted(image_files, key=lambda p: int(os.path.splitext(os.path.basename(p))[0]))

        if not image_files:
            logger.info("carousel: no images downloaded for %s", url)
            return None

        slides = []
        for i, image_path in enumerate(image_files, 1):
            try:
                text = vision.extract_text_from_image(image_path)
                if text.strip():
                    slides.append(f"[Слайд {i}]\n{text.strip()}")
            except Exception as e:
                logger.info("carousel: OCR failed for slide %d (%s)", i, e)

        return "\n\n".join(slides) if slides else None


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
