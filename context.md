# Context — content-bot
_Updated: 2026-05-18_

## Session 2026-05-18
### Progress
- headless-pm v0.7.7 installed: /pm-save skill now available
- pm-save smoke test run in this workspace (first real test)
- Opening Dashboard verified in pm skill code — ASCII kanban (DISCOVERY→DEFINE→BUILD→SHIP) reads .pm/STATE.md + artifacts/
- Agent Communication Protocol confirmed in all 24 agents (▶ opening / ✓ closing blocks)
- orchestrator.log format will shift from timestamp lines to markdown blocks after this save

### Decisions
- pm-save uses `git add .pm/` to commit situation.md automatically (no manual update needed)
- orchestrator.log: markdown blocks prepended at top (grep-friendly)
- pm-save named in pm-* namespace (not /save) for global product consistency

### Next Steps
1. Run `/pm` from content-bot/ to test Opening Dashboard + pm-radar live
2. Run pm-hypothesis or pm-sprint to test Agent Communication Protocol blocks
3. Verify Module 6 PRD scope — prd.md exists, check if sprint planning is next

### Open Questions
- Instagram ingest: throwaway account ready? INSTAGRAM_USERNAME/PASSWORD set on Render?
- YouTube transcript: proxy validation done on 5 real URLs?

---

## Сессия 2026-04-19
### Прогресс
- Модуль 2 полностью реализован и задеплоен: Gemini анализ при инжесте + Google Sheets sync + фоновый поллер для генерации скриптов
- Исправлен баг записи в Sheets (строки попадали в 1001-1002 из-за data validation) — переключились на col_values(1) + sheet.update()
- Добавлен retry для Gemini 429 (3 попытки с задержкой 20s)
- Убран невалидный kwarg `proxies` из YouTubeTranscriptApi (установленная версия не поддерживает)
- Добавлено debug логирование в _download_audio для захвата ошибки yt-dlp
- Исправлен тест test_append_row после переписывания логики append_row
- Создан BACKLOG.md с открытыми задачами и вариантами решения

### Решения
- col_values(1) вместо sheet.append_row() — append_row считает data validation rows непустыми
- Retry Gemini 429 в цикле внутри analyzer.py, не на уровне caller
- YouTubeTranscriptApi() без прокси — проксирование через yt-dlp при аудио загрузке

### Следующие шаги
1. Выбрать вариант для Gemini квоты: A (биллинг Google AI Studio), B (Groq Llama), или C (ждать)
2. Проверить YouTube транскрипт: отправить URL в бота, поймать строку `WARNING: yt-dlp audio download failed` в логах Render
3. По логам yt-dlp — решить нужны ли cookies/другой прокси для YouTube

### Открытые вопросы
- Gemini free tier дневной лимит исчерпан — варианты A/B/C в BACKLOG.md
- YouTube транскрипт не извлекается — конкретная ошибка yt-dlp пока не поймана (debug logging задеплоен)
