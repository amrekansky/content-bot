import pytest
from unittest.mock import patch, MagicMock
from content_bot.services.sheets import (
    append_row,
    get_approved_rows,
    update_status,
    update_scripts,
    ApprovedRow,
)


def _make_sheet_mock(rows=None):
    sheet = MagicMock()
    sheet.get_all_values.return_value = rows or []
    return sheet


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_append_row_adds_row(mock_get_sheet):
    sheet = MagicMock()
    sheet.col_values.return_value = ["ID"]  # header only → next_row = 2
    mock_get_sheet.return_value = sheet

    append_row(1, "https://tiktok.com/v/123", "tiktok", "Test video",
               "transcript text", "analysis text")

    sheet.update.assert_called_once()
    call_range, call_data = sheet.update.call_args[0]
    assert call_range == "A2"
    row = call_data[0]
    assert row[0] == 1                 # ID
    assert row[1] == "https://tiktok.com/v/123"
    assert row[7] == "новый"           # Статус


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_append_row_skipped_when_no_credentials(mock_get_sheet):
    with patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", None):
        append_row(1, "https://tiktok.com/v/123", "tiktok", "Test", "t", "a")
    mock_get_sheet.assert_not_called()


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_approved_rows_returns_approved(mock_get_sheet):
    header = ["ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
              "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
              "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт"]
    row = ["42", "https://t.com", "tiktok", "title", "2026-04-18",
           "transcript", "analysis", "одобрено",
           "TRUE", "FALSE", "FALSE", "FALSE",
           "", "", "", ""]
    sheet = _make_sheet_mock(rows=[header, row])
    mock_get_sheet.return_value = sheet

    result = get_approved_rows()

    assert len(result) == 1
    assert result[0].content_id == 42
    assert result[0].tiktok is True
    assert result[0].telegram is False
    assert result[0].row_num == 2


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_approved_rows_skips_non_approved(mock_get_sheet):
    header = ["ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
              "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
              "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт"]
    row = ["42", "https://t.com", "tiktok", "title", "2026-04-18",
           "transcript", "analysis", "новый",
           "TRUE", "FALSE", "FALSE", "FALSE",
           "", "", "", ""]
    sheet = _make_sheet_mock(rows=[header, row])
    mock_get_sheet.return_value = sheet

    result = get_approved_rows()
    assert result == []


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_update_status_calls_update_cell(mock_get_sheet):
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    update_status(3, "в работе")

    sheet.update_cell.assert_called_once_with(3, 8, "в работе")


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_update_scripts_writes_tiktok_and_telegram(mock_get_sheet):
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    update_scripts(3, {"tiktok": "tiktok text", "telegram": "telegram text"})

    calls = [c[0] for c in sheet.update_cell.call_args_list]
    assert (3, 13, "tiktok text") in calls
    assert (3, 14, "telegram text") in calls


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_scheduled_rows_returns_ready_with_date(mock_get_sheet):
    from content_bot.services.sheets import get_scheduled_rows
    header = [
        "ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
        "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
        "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт",
        "Дата публикации","В календаре ✓",
    ]
    row = [
        "5","https://t.com","tiktok","Мой заголовок","2026-04-20",
        "transcript","analysis","готово",
        "FALSE","TRUE","FALSE","FALSE",
        "","скрипт","","",
        "2026-04-25 18:00","",
    ]
    mock_get_sheet.return_value = _make_sheet_mock(rows=[header, row])

    result = get_scheduled_rows()

    assert len(result) == 1
    assert result[0].title == "Мой заголовок"
    assert result[0].publish_date_str == "2026-04-25 18:00"
    assert result[0].telegram is True
    assert result[0].tiktok is False
    assert result[0].row_num == 2


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_scheduled_rows_skips_already_calendared(mock_get_sheet):
    from content_bot.services.sheets import get_scheduled_rows
    header = [
        "ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
        "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
        "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт",
        "Дата публикации","В календаре ✓",
    ]
    row = [
        "5","https://t.com","tiktok","Заголовок","2026-04-20",
        "transcript","analysis","готово",
        "FALSE","TRUE","FALSE","FALSE",
        "","скрипт","","",
        "2026-04-25 18:00","TRUE",
    ]
    mock_get_sheet.return_value = _make_sheet_mock(rows=[header, row])

    assert get_scheduled_rows() == []


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_scheduled_rows_skips_missing_date(mock_get_sheet):
    from content_bot.services.sheets import get_scheduled_rows
    header = [
        "ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
        "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
        "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт",
        "Дата публикации","В календаре ✓",
    ]
    row = [
        "5","https://t.com","tiktok","Заголовок","2026-04-20",
        "transcript","analysis","готово",
        "FALSE","TRUE","FALSE","FALSE",
        "","скрипт","","",
        "","",
    ]
    mock_get_sheet.return_value = _make_sheet_mock(rows=[header, row])

    assert get_scheduled_rows() == []


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_mark_calendared_sets_flag_and_status(mock_get_sheet):
    from content_bot.services.sheets import mark_calendared
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    mark_calendared(4)

    calls = [c[0] for c in sheet.update_cell.call_args_list]
    assert (4, 18, True) in calls
    assert (4, 8, "запланировано") in calls


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_due_posts_returns_telegram_due_row(mock_get_sheet):
    from content_bot.services.sheets import get_due_posts
    header = [
        "ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
        "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
        "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт",
        "Дата публикации","В календаре ✓","Опубликовано ✓",
    ]
    row = [
        "1","https://t.com","tiktok","Мой заголовок","2026-04-20",
        "transcript","analysis","запланировано",
        "FALSE","TRUE","FALSE","FALSE",
        "","Текст поста телеграм","","",
        "2026-04-21 10:00","TRUE","",
    ]
    mock_get_sheet.return_value = _make_sheet_mock(rows=[header, row])

    from unittest.mock import patch as _patch
    from datetime import datetime
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Asia/Almaty")
    fake_now = datetime(2026, 4, 21, 12, 0, tzinfo=_TZ)

    with _patch("content_bot.services.sheets._now_almaty", return_value=fake_now):
        result = get_due_posts()

    assert len(result) == 1
    assert result[0].title == "Мой заголовок"
    assert result[0].telegram_script == "Текст поста телеграм"
    assert result[0].row_num == 2


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_due_posts_skips_future_date(mock_get_sheet):
    from content_bot.services.sheets import get_due_posts
    header = [
        "ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
        "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
        "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт",
        "Дата публикации","В календаре ✓","Опубликовано ✓",
    ]
    row = [
        "1","https://t.com","tiktok","Заголовок","2026-04-20",
        "transcript","analysis","запланировано",
        "FALSE","TRUE","FALSE","FALSE",
        "","Текст поста","","",
        "2026-04-30 18:00","TRUE","",
    ]
    mock_get_sheet.return_value = _make_sheet_mock(rows=[header, row])

    from unittest.mock import patch as _patch
    from datetime import datetime
    from zoneinfo import ZoneInfo
    fake_now = datetime(2026, 4, 21, 12, 0, tzinfo=ZoneInfo("Asia/Almaty"))

    with _patch("content_bot.services.sheets._now_almaty", return_value=fake_now):
        result = get_due_posts()

    assert result == []


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_due_posts_skips_already_published(mock_get_sheet):
    from content_bot.services.sheets import get_due_posts
    header = [
        "ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
        "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
        "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт",
        "Дата публикации","В календаре ✓","Опубликовано ✓",
    ]
    row = [
        "1","https://t.com","tiktok","Заголовок","2026-04-20",
        "transcript","analysis","опубликовано",
        "FALSE","TRUE","FALSE","FALSE",
        "","Текст поста","","",
        "2026-04-21 10:00","TRUE","TRUE",
    ]
    mock_get_sheet.return_value = _make_sheet_mock(rows=[header, row])

    from unittest.mock import patch as _patch
    from datetime import datetime
    from zoneinfo import ZoneInfo
    fake_now = datetime(2026, 4, 21, 12, 0, tzinfo=ZoneInfo("Asia/Almaty"))

    with _patch("content_bot.services.sheets._now_almaty", return_value=fake_now):
        result = get_due_posts()

    assert result == []


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_get_all_publish_dates_returns_non_empty(mock_get_sheet):
    from content_bot.services.sheets import get_all_publish_dates
    header = ["ID","URL","Платформа","Название","Дата","Транскрипт","Анализ","Статус",
              "TikTok ✓","Telegram ✓","LinkedIn ✓","YouTube ✓",
              "TikTok скрипт","Telegram пост","LinkedIn пост","YouTube скрипт",
              "Дата публикации","В календаре ✓","Опубликовано ✓"]
    row1 = ["1","","","","","","","","","","","","","","","","2026-04-25 18:00","",""]
    row2 = ["2","","","","","","","","","","","","","","","","","",""]
    mock_get_sheet.return_value = _make_sheet_mock(rows=[header, row1, row2])

    result = get_all_publish_dates()
    assert result == ["2026-04-25 18:00"]


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_assign_date_writes_to_col_17(mock_get_sheet):
    from content_bot.services.sheets import assign_date
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    assign_date(5, "2026-04-25 18:00")

    sheet.update_cell.assert_called_once_with(5, 17, "2026-04-25 18:00")


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_update_title_writes_to_col_4(mock_get_sheet):
    from content_bot.services.sheets import update_title
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    update_title(3, "Мой SEO заголовок")

    sheet.update_cell.assert_called_once_with(3, 4, "Мой SEO заголовок")


@patch("content_bot.services.sheets.GOOGLE_SHEETS_ID", "fake-id")
@patch("content_bot.services.sheets.GOOGLE_SHEETS_CREDENTIALS", '{"type":"service_account"}')
@patch("content_bot.services.sheets._get_sheet")
def test_mark_published_sets_col19_and_status(mock_get_sheet):
    from content_bot.services.sheets import mark_published
    sheet = _make_sheet_mock()
    mock_get_sheet.return_value = sheet

    mark_published(6)

    calls = [c[0] for c in sheet.update_cell.call_args_list]
    assert (6, 19, True) in calls
    assert (6, 8, "опубликовано") in calls
