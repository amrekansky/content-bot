# Proxy Fix + Tutorial Storytelling Design

_Date: 2026-04-17_

## Goal

Two changes:
1. Fix transcript extraction on Render by routing yt-dlp through a residential proxy
2. Update TUTORIAL.md with a storytelling narrative of the debugging journey, highlighting /brainstorming as the turning point

---

## Part 1: Residential Proxy for yt-dlp

### Problem

Render runs on shared datacenter infrastructure. YouTube and TikTok detect datacenter IPs and block all download requests — both subtitle extraction and audio download. This means yt-dlp fails immediately, Groq Whisper never gets an audio file, and the transcript is always empty. Three code fixes were applied correctly but attacked the wrong layer of the problem.

### Solution

Add an optional `WEBSHARE_PROXY_URL` environment variable. When set, both yt-dlp invocations receive a `--proxy` flag pointing to a Webshare rotating residential proxy. When absent, behavior is unchanged.

### Files

- `content_bot/config.py` — add `WEBSHARE_PROXY_URL: str | None = os.environ.get("WEBSHARE_PROXY_URL")`
- `content_bot/services/content_processor.py` — pass `--proxy` to `_extract_subtitles()` and `_download_audio()` when `WEBSHARE_PROXY_URL` is set
- `.env.example` — add `WEBSHARE_PROXY_URL=` with comment

### Proxy URL format (Webshare)

```
http://<username>-rotate:<password>@p.webshare.io:80
```

User registers at webshare.io (free tier: 10 proxies, 1GB/month), copies the rotating proxy URL from the dashboard, adds it to Render environment variables.

### Behavior after fix

| Platform  | Step 1              | Step 2 (if Step 1 fails) | Step 3 (last resort)   |
|-----------|---------------------|--------------------------|------------------------|
| YouTube   | youtube-transcript-api | Groq Whisper via yt-dlp + proxy | yt-dlp subtitles via proxy |
| TikTok    | yt-dlp subtitles via proxy | Groq Whisper via yt-dlp + proxy | — |
| Instagram | yt-dlp subtitles via proxy | Groq Whisper via yt-dlp + proxy | — |

---

## Part 2: TUTORIAL.md Storytelling

### Audience

GitHub visitors discovering the repo. Not course students — README stays unchanged.

### Narrative structure

Three acts added as a new section **"How transcript extraction was built"** inside TUTORIAL.md, placed after the architecture overview, before the deployment steps.

**Act 1 — It's deployed, it works... mostly**

Bot starts, DB saves entries, cards post to archive channel. Everything looks good. But the transcript field is always empty. First assumption: wrong API usage.

**Act 2 — Three fixes, same result**

- Fix 1: `youtube-transcript-api` — API changed in version 0.7+ (`get_transcript` class method removed). Fixed the call. Still no transcript.
- Fix 2: Added Groq Whisper as fallback — download audio via yt-dlp, transcribe with Whisper. Still no transcript. Processing time: 6 seconds for a 34-minute video. Something is wrong at a deeper level.
- Fix 3: Added Groq Whisper fallback for TikTok/Instagram too. Still nothing.

Each fix was correct code. None fixed the actual problem.

**Act 3 — /brainstorming as a diagnostic tool**

Instead of Fix 4, switched to `/brainstorming` mode. Stopped executing, started diagnosing. Mapped the full extraction chain. Realized: Render is a shared datacenter. YouTube and TikTok detect datacenter IPs and block all download requests at the network level. yt-dlp was failing in milliseconds before any audio was touched. All three fixes were solving the wrong problem.

Decision: route yt-dlp through a residential proxy (Webshare). One env var, all platforms fixed.

**Lesson for the reader:**

> `/brainstorming` isn't for when you're stuck after one try. It's for when three correct fixes don't work and you're about to write Fix 4. That's when you need to exit execution mode.

---

## Out of scope

- README changes (no changes)
- Switching hosting provider
- YouTube Data API v3 (residential proxy covers all platforms uniformly)
