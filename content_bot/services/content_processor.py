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
    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "ru,en",
        "--skip-download",
        "--output", os.path.join(tmp_dir, "%(id)s"),
        url,
    ]
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
    """Try youtube-transcript-api first, fall back to yt-dlp."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        import re as _re
        video_id_match = _re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
        if not video_id_match:
            return None
        video_id = video_id_match.group(1)
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["ru", "en"]
        )
        text = " ".join(entry["text"] for entry in transcript_list)
        return text.strip() or None
    except Exception as e:
        logger.info("youtube-transcript-api failed (%s), trying yt-dlp", e)

    with tempfile.TemporaryDirectory() as tmp_dir:
        return _extract_subtitles(url, tmp_dir)


def process_url(url: str) -> ProcessedContent | None:
    """Process a URL: detect type, extract transcript. Returns None for unknown URLs."""
    url_info = detect_url_type(url)
    if url_info is None:
        return None

    platform = url_info["platform"]
    content_type = url_info["content_type"]

    if platform == "youtube":
        transcript = _extract_youtube_transcript(url)
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            transcript = _extract_subtitles(url, tmp_dir)

    return ProcessedContent(
        platform=platform,
        content_type=content_type,
        transcript=transcript,
        source_url=url,
    )
