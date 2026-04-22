# Content Bot — Backlog

## Открытые задачи

### [MEDIUM] Instagram — throwaway аккаунт

Код для instaloader готов и задеплоен. Нужно создать throwaway Instagram аккаунт и добавить в Render:
- `INSTAGRAM_USERNAME`
- `INSTAGRAM_PASSWORD`

После этого Instagram Reels и карусели заработают.

---

### [LOW] YouTube транскрипт — проверить стабильность через прокси

Webshare прокси добавлен, Groq Whisper как fallback работает. Нужно проверить на нескольких YouTube URL что транскрипт реально извлекается стабильно.

---

### [LOW] TikTok карусели (`/photo/` URL)

yt-dlp не поддерживает формат. Решения нет без стороннего API. Нишевый кейс — принять как ограничение.

---

## Закрытые задачи

- ~~Gemini квота~~ — решено: переключились на Claude Haiku API
- ~~JSON фенсинг от Claude~~ — решено: regex strip перед json.loads
- ~~YouTube/TikTok блокировка на Render~~ — решено: Webshare residential proxy
- ~~Токен бота в логах~~ — решено: httpx лог уровень WARNING + ротация токена
- ~~Нет уведомлений о готовом контенте~~ — решено: Google Calendar интеграция (Модуль 3)
- ~~Ручная публикация~~ — решено: автопубликация по расписанию (Модуль 4)
- ~~Нет удобного редактора постов~~ — решено: Google Drive/Docs sync (Модуль 5)
