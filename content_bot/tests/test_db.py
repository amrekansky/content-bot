import os
import pytest
import psycopg2
from content_bot.database.db import init_db, insert_content, get_content_by_id


@pytest.fixture(scope="session")
def db_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set — skipping DB tests")
    return url


@pytest.fixture(autouse=True)
def cleanup(db_url):
    yield
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("DELETE FROM library_content WHERE source_url LIKE 'https://test.%'")
    conn.commit()
    cur.close()
    conn.close()


def test_init_db_creates_table(db_url):
    init_db()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name = 'library_content'
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    assert row is not None


def test_insert_and_fetch(db_url):
    init_db()
    content_id = insert_content(
        source_url="https://test.youtube.com/watch?v=abc123",
        platform="youtube",
        content_type="video",
        transcript="Test transcript content here",
    )
    assert isinstance(content_id, int)
    assert content_id > 0

    row = get_content_by_id(content_id)
    assert row["source_url"] == "https://test.youtube.com/watch?v=abc123"
    assert row["platform"] == "youtube"
    assert row["transcript"] == "Test transcript content here"
    assert row["status"] == "analyzed"


def test_insert_without_transcript(db_url):
    init_db()
    content_id = insert_content(
        source_url="https://test.tiktok.com/v/1",
        platform="tiktok",
        content_type="video_short",
        transcript=None,
    )
    row = get_content_by_id(content_id)
    assert row["transcript"] is None
    assert row["status"] == "analyzed"


def test_get_nonexistent_returns_none():
    init_db()
    row = get_content_by_id(999999999)
    assert row is None
