import psycopg2
import psycopg2.extras
from content_bot.config import DATABASE_URL


def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db() -> None:
    """Create library_content table if it doesn't exist."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS library_content (
                id              SERIAL PRIMARY KEY,
                source_url      TEXT NOT NULL,
                platform        VARCHAR(20) NOT NULL,
                content_type    VARCHAR(20) NOT NULL,
                transcript      TEXT,
                status          VARCHAR(20) NOT NULL DEFAULT 'analyzed',
                created_at      TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
    finally:
        conn.close()


def insert_content(
    source_url: str,
    platform: str,
    content_type: str,
    transcript: str | None,
) -> int:
    """Insert a content record and return its id."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO library_content (source_url, platform, content_type, transcript)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (source_url, platform, content_type, transcript),
        )
        content_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return content_id
    finally:
        conn.close()


def get_content_by_id(content_id: int) -> dict | None:
    """Return a content record as a dict, or None if not found."""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM library_content WHERE id = %s", (content_id,))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    finally:
        conn.close()
