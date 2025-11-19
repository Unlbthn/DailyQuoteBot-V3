import sqlite3
import datetime

DB_PATH = "bot.db"

_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row


def init_db():
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'tr',
            daily_enabled INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            lang TEXT,
            quote_text TEXT,
            quote_tr TEXT,
            author TEXT,
            created_at TEXT
        )
        """
    )
    _conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            user_id INTEGER,
            category TEXT,
            created_at TEXT
        )
        """
    )
    _conn.commit()


def db_execute(query: str, params: tuple = ()):
    cur = _conn.execute(query, params)
    _conn.commit()
    return cur


def ensure_user(user_id: int):
    now = datetime.datetime.utcnow().isoformat()
    db_execute(
        "INSERT OR IGNORE INTO users (user_id, created_at) VALUES (?, ?)",
        (user_id, now),
    )


def get_user_lang(user_id: int) -> str:
    cur = db_execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row and row["lang"]:
        return row["lang"]
    ensure_user(user_id)
    db_execute("UPDATE users SET lang = ? WHERE user_id = ?", ("tr", user_id))
    return "tr"


def set_user_lang(user_id: int, lang: str):
    ensure_user(user_id)
    db_execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))


def set_daily_enabled(user_id: int, enabled: bool):
    ensure_user(user_id)
    db_execute(
        "UPDATE users SET daily_enabled = ? WHERE user_id = ?",
        (1 if enabled else 0, user_id),
    )


def get_daily_enabled(user_id: int) -> bool:
    cur = db_execute("SELECT daily_enabled FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        ensure_user(user_id)
        return True
    return bool(row["daily_enabled"])


def log_stat(event_type: str, user_id: int | None, category: str | None):
    now = datetime.datetime.utcnow().isoformat()
    db_execute(
        "INSERT INTO stats (event_type, user_id, category, created_at) VALUES (?, ?, ?, ?)",
        (event_type, user_id, category, now),
    )


def add_favorite(
    user_id: int,
    category: str,
    lang: str,
    quote_text: str,
    quote_tr: str | None,
    author: str,
):
    now = datetime.datetime.utcnow().isoformat()
    db_execute(
        """
        INSERT INTO favorites (user_id, category, lang, quote_text, quote_tr, author, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, category, lang, quote_text, quote_tr, author, now),
    )


def get_last_favorites(user_id: int, limit: int = 10):
    cur = db_execute(
        """
        SELECT category, lang, quote_text, quote_tr, author, created_at
        FROM favorites
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    return cur.fetchall()


def get_stats_summary():
    total_users = db_execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    daily_users = db_execute(
        "SELECT COUNT(*) AS c FROM users WHERE daily_enabled = 1"
    ).fetchone()["c"]
    total_favs = db_execute("SELECT COUNT(*) AS c FROM favorites").fetchone()["c"]
    ad_shown_count = db_execute(
        "SELECT COUNT(*) AS c FROM stats WHERE event_type = 'ad_shown'"
    ).fetchone()["c"]

    top_cat_views_row = db_execute(
        """
        SELECT category, COUNT(*) AS c
        FROM stats
        WHERE category IS NOT NULL
          AND event_type IN ('quote_today','quote_random','quote_category')
        GROUP BY category
        ORDER BY c DESC
        LIMIT 1
        """
    ).fetchone()

    top_cat_favs_row = db_execute(
        """
        SELECT category, COUNT(*) AS c
        FROM favorites
        GROUP BY category
        ORDER BY c DESC
        LIMIT 1
        """
    ).fetchone()

    return {
        "total_users": total_users,
        "daily_users": daily_users,
        "total_favs": total_favs,
        "ad_shown_count": ad_shown_count,
        "top_cat_views_row": top_cat_views_row,
        "top_cat_favs_row": top_cat_favs_row,
    }


# Modül import edildiğinde DB şemasını oluştur
init_db()
