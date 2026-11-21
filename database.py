
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "cards.db"

CARD_COUNTER = "next_card_id"
COMMENT_COUNTER = "next_comment_id"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _seed_counter(connection, name: str, table: str):
    """Ensure a counter is at least one greater than the largest stored ID."""

    maximum = connection.execute(
        f"SELECT COALESCE(MAX(id), 0) FROM {table}"
    ).fetchone()[0]
    minimum = maximum + 1

    row = connection.execute(
        "SELECT value FROM counters WHERE name = ?",
        (name,),
    ).fetchone()

    if row is None:
        connection.execute(
            "INSERT INTO counters (name, value) VALUES (?, ?)",
            (name, minimum),
        )
    elif row["value"] < minimum:
        connection.execute(
            "UPDATE counters SET value = ? WHERE name = ?",
            (minimum, name),
        )


def _bump_counter(connection, name: str, minimum: int):
    """Raise a counter to at least the supplied minimum value."""

    row = connection.execute(
        "SELECT value FROM counters WHERE name = ?",
        (name,),
    ).fetchone()

    if row is None:
        connection.execute(
            "INSERT INTO counters (name, value) VALUES (?, ?)",
            (name, minimum),
        )
    elif row["value"] < minimum:
        connection.execute(
            "UPDATE counters SET value = ? WHERE name = ?",
            (minimum, name),
        )


def _get_counter(connection, name: str) -> int:
    row = connection.execute(
        "SELECT value FROM counters WHERE name = ?",
        (name,),
    ).fetchone()
    return row["value"] if row is not None else 1


def initialize_database():
    """Create database tables if they do not exist."""

    connection = get_connection()

    try:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'spec',
                    assignee TEXT
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY,
                    card_id INTEGER NOT NULL,
                    author TEXT NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY (card_id) REFERENCES cards(id)
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS counters (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
            """)

            # Authentication tables. These are additive only and never
            # touch existing cards, comments, or counters.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                        CHECK (role IN ('admin', 'member')),
                    created_at TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Existing databases created before the counters table must
            # continue IDs from their highest stored IDs.
            _seed_counter(connection, CARD_COUNTER, "cards")
            _seed_counter(connection, COMMENT_COUNTER, "comments")
    finally:
        connection.close()


def create_card(card: dict):
    """Insert a new card and advance the persistent card ID counter."""

    connection = get_connection()

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO cards (
                    id, title, description, status, assignee
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    card["id"],
                    card["title"],
                    card["description"],
                    card["status"],
                    card.get("assignee"),
                ),
            )
            _bump_counter(
                connection,
                CARD_COUNTER,
                card["id"] + 1,
            )
    finally:
        connection.close()


def save_card(card: dict):
    """Insert or update a card in SQLite."""

    connection = get_connection()

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO cards (
                    id, title, description, status, assignee
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    status = excluded.status,
                    assignee = excluded.assignee
                """,
                (
                    card["id"],
                    card["title"],
                    card["description"],
                    card["status"],
                    card.get("assignee"),
                ),
            )
    finally:
        connection.close()


def load_cards():
    """Load all saved cards from SQLite."""

    connection = get_connection()

    try:
        rows = connection.execute(
            "SELECT * FROM cards ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]


def create_comment(comment: dict):
    """Insert a new comment and advance the persistent comment ID counter."""

    connection = get_connection()

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO comments (
                    id, card_id, author, text
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    comment["id"],
                    comment["card_id"],
                    comment["author"],
                    comment["text"],
                ),
            )
            _bump_counter(
                connection,
                COMMENT_COUNTER,
                comment["id"] + 1,
            )
    finally:
        connection.close()


def load_comments():
    """Load all saved comments from SQLite."""

    connection = get_connection()

    try:
        rows = connection.execute(
            "SELECT * FROM comments ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]


def delete_card(card_id: int) -> bool:
    """Delete a card together with its comments in one transaction."""

    connection = get_connection()

    try:
        with connection:
            connection.execute(
                "DELETE FROM comments WHERE card_id = ?",
                (card_id,),
            )
            cursor = connection.execute(
                "DELETE FROM cards WHERE id = ?",
                (card_id,),
            )
    finally:
        connection.close()

    return cursor.rowcount > 0


def get_next_ids():
    """Return the persisted next card and comment IDs."""

    connection = get_connection()

    try:
        return (
            _get_counter(connection, CARD_COUNTER),
            _get_counter(connection, COMMENT_COUNTER),
        )
    finally:
        connection.close()


def create_user(
    username: str,
    password_hash: str,
    role: str,
    created_at: str,
) -> int:
    """Insert an authentication user and return its ID."""

    connection = get_connection()

    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    username, password_hash, role, created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, role, created_at),
            )
    finally:
        connection.close()

    return cursor.lastrowid


def get_user_by_username(username: str):
    """Return a user row by username, or None."""

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        connection.close()

    return dict(row) if row is not None else None


def get_user_by_id(user_id: int):
    """Return a user row by ID, or None."""

    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    return dict(row) if row is not None else None


def count_users() -> int:
    """Return the number of authentication users."""

    connection = get_connection()

    try:
        return connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]
    finally:
        connection.close()


def create_session(
    token_hash: str,
    user_id: int,
    expires_at: str,
):
    """Persist a hashed bearer token with its expiry."""

    connection = get_connection()

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO sessions (token_hash, user_id, expires_at)
                VALUES (?, ?, ?)
                """,
                (token_hash, user_id, expires_at),
            )
    finally:
        connection.close()


def get_session(token_hash: str):
    """Return a session joined with its user, or None."""

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                sessions.token_hash,
                sessions.user_id,
                sessions.expires_at,
                users.username,
                users.role
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
    finally:
        connection.close()

    return dict(row) if row is not None else None


def delete_session(token_hash: str):
    """Delete a single session by token hash."""

    connection = get_connection()

    try:
        with connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?",
                (token_hash,),
            )
    finally:
        connection.close()


def delete_expired_sessions(now_iso: str):
    """Delete sessions whose expiry is at or before the given time."""

    connection = get_connection()

    try:
        with connection:
            connection.execute(
                "DELETE FROM sessions WHERE expires_at <= ?",
                (now_iso,),
            )
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print("SQLite database initialized successfully!")
