"""SQLite storage for published articles.

Conversation and Thought Map tables remain for the earlier prototype. The
current flow stores only an article title, body, and author. The database
lives in the gitignored data directory.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import Conversation, ThoughtMap


def data_dir() -> Path:
    override = os.environ.get("THOUGHTPAGE_DATA_DIR", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data"


def ensure_dirs() -> Path:
    root = data_dir()
    (root / "originals").mkdir(parents=True, exist_ok=True)
    return root


@contextmanager
def _db():
    ensure_dirs()
    connection = sqlite3.connect(data_dir() / "thoughtpage.db")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            original_text TEXT NOT NULL,
            original_file TEXT NOT NULL,
            parse_warnings TEXT NOT NULL,
            messages_json TEXT NOT NULL,
            extraction_status TEXT NOT NULL,
            extraction_error TEXT
        );
        CREATE TABLE IF NOT EXISTS thought_maps (
            thought_map_id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL UNIQUE,
            original_json TEXT NOT NULL,
            current_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        );
        CREATE TABLE IF NOT EXISTS articles (
            article_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author_name TEXT NOT NULL,
            author_email TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


@dataclass
class StoredConversation:
    conversation: Conversation
    extraction_status: str
    extraction_error: str | None
    original_file: str


@dataclass
class StoredThoughtMap:
    original: ThoughtMap
    current: ThoughtMap


def save_conversation(conversation: Conversation) -> Path:
    root = ensure_dirs()
    original = root / "originals" / f"{conversation.conversation_id}.md"
    payload = conversation.model_dump(mode="json")
    original.write_text(conversation.original_text, encoding="utf-8")
    try:
        with _db() as connection:
            connection.execute(
                """
                INSERT INTO conversations (
                    conversation_id, title, source_type, created_at, original_text,
                    original_file, parse_warnings, messages_json,
                    extraction_status, extraction_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'not_started', NULL)
                """,
                (
                    conversation.conversation_id,
                    conversation.title,
                    conversation.source_type,
                    payload["created_at"],
                    conversation.original_text,
                    str(original),
                    json.dumps(conversation.parse_warnings),
                    json.dumps(payload["messages"]),
                ),
            )
    except Exception:
        if original.exists():
            original.unlink()
        raise
    return original


def list_conversations() -> list[dict]:
    with _db() as connection:
        rows = connection.execute(
            """
            SELECT conversation_id, title, source_type, created_at,
                   extraction_status, messages_json
            FROM conversations
            ORDER BY created_at DESC
            """
        ).fetchall()
    listed = []
    for row in rows:
        listed.append(
            {
                "conversation_id": row["conversation_id"],
                "title": row["title"],
                "source_type": row["source_type"],
                "created_at": row["created_at"],
                "extraction_status": row["extraction_status"],
                "message_count": len(json.loads(row["messages_json"])),
            }
        )
    return listed


def get_conversation(conversation_id: str) -> StoredConversation | None:
    with _db() as connection:
        row = connection.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    if row is None:
        return None
    conversation = Conversation.model_validate(
        {
            "conversation_id": row["conversation_id"],
            "title": row["title"],
            "source_type": row["source_type"],
            "created_at": row["created_at"],
            "original_text": row["original_text"],
            "messages": json.loads(row["messages_json"]),
            "parse_warnings": json.loads(row["parse_warnings"]),
        }
    )
    return StoredConversation(
        conversation=conversation,
        extraction_status=row["extraction_status"],
        extraction_error=row["extraction_error"],
        original_file=row["original_file"],
    )


def set_extraction_status(conversation_id: str, status: str, error: str | None) -> None:
    with _db() as connection:
        connection.execute(
            """
            UPDATE conversations
            SET extraction_status = ?, extraction_error = ?
            WHERE conversation_id = ?
            """,
            (status, error, conversation_id),
        )


def save_new_thought_map(thought_map: ThoughtMap) -> None:
    raw = thought_map.model_dump(mode="json")
    encoded = json.dumps(raw)
    with _db() as connection:
        connection.execute(
            "DELETE FROM thought_maps WHERE conversation_id = ?",
            (thought_map.conversation_id,),
        )
        connection.execute(
            """
            INSERT INTO thought_maps (
                thought_map_id, conversation_id, original_json, current_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                thought_map.thought_map_id,
                thought_map.conversation_id,
                encoded,
                encoded,
                raw["created_at"],
                raw["updated_at"],
            ),
        )


def save_current(thought_map: ThoughtMap) -> None:
    raw = thought_map.model_dump(mode="json")
    with _db() as connection:
        cursor = connection.execute(
            """
            UPDATE thought_maps
            SET current_json = ?, updated_at = ?
            WHERE thought_map_id = ?
            """,
            (json.dumps(raw), raw["updated_at"], thought_map.thought_map_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("That Thought Map is not in private storage.")


def get_thought_map(thought_map_id: str) -> StoredThoughtMap | None:
    with _db() as connection:
        row = connection.execute(
            "SELECT original_json, current_json FROM thought_maps WHERE thought_map_id = ?",
            (thought_map_id,),
        ).fetchone()
    return _stored_map(row)


def get_thought_map_for_conversation(conversation_id: str) -> StoredThoughtMap | None:
    with _db() as connection:
        row = connection.execute(
            "SELECT original_json, current_json FROM thought_maps WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    return _stored_map(row)


def list_thought_maps() -> list[dict]:
    with _db() as connection:
        rows = connection.execute(
            """
            SELECT tm.thought_map_id, tm.conversation_id, tm.updated_at, tm.current_json, c.title
            FROM thought_maps tm
            JOIN conversations c ON c.conversation_id = tm.conversation_id
            ORDER BY tm.updated_at DESC
            """
        ).fetchall()
    listed = []
    for row in rows:
        current = json.loads(row["current_json"])
        listed.append(
            {
                "thought_map_id": row["thought_map_id"],
                "conversation_id": row["conversation_id"],
                "title": row["title"],
                "updated_at": row["updated_at"],
                "review_status": current.get("review_status", "pending"),
                "item_count": len(current.get("thought_items", [])),
            }
        )
    return listed


def delete_conversation(conversation_id: str) -> bool:
    with _db() as connection:
        row = connection.execute(
            "SELECT original_file FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            return False
        connection.execute(
            "DELETE FROM thought_maps WHERE conversation_id = ?",
            (conversation_id,),
        )
        connection.execute(
            "DELETE FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        )
    _delete_original(Path(row["original_file"]))
    return True


def _stored_map(row: sqlite3.Row | None) -> StoredThoughtMap | None:
    if row is None:
        return None
    return StoredThoughtMap(
        original=ThoughtMap.model_validate(json.loads(row["original_json"])),
        current=ThoughtMap.model_validate(json.loads(row["current_json"])),
    )


@dataclass(frozen=True)
class Article:
    article_id: str
    title: str
    content: str
    author_name: str
    author_email: str
    created_at: str


def save_article(*, title: str, content: str, author_name: str, author_email: str) -> Article:
    article = Article(
        article_id=str(uuid.uuid4()),
        title=title,
        content=content,
        author_name=author_name,
        author_email=author_email,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    with _db() as connection:
        connection.execute(
            """
            INSERT INTO articles (article_id, title, content, author_name, author_email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                article.article_id,
                article.title,
                article.content,
                article.author_name,
                article.author_email,
                article.created_at,
            ),
        )
    return article


def list_articles() -> list[Article]:
    with _db() as connection:
        rows = connection.execute(
            "SELECT * FROM articles ORDER BY created_at DESC, article_id DESC"
        ).fetchall()
    return [_article(row) for row in rows]


def update_article(article_id: str, *, title: str, content: str) -> Article | None:
    with _db() as connection:
        cursor = connection.execute(
            "UPDATE articles SET title = ?, content = ? WHERE article_id = ?",
            (title, content, article_id),
        )
        if cursor.rowcount == 0:
            return None
    return get_article(article_id)


def get_article(article_id: str) -> Article | None:
    with _db() as connection:
        row = connection.execute(
            "SELECT * FROM articles WHERE article_id = ?",
            (article_id,),
        ).fetchone()
    if row is None:
        return None
    return _article(row)


def _article(row: sqlite3.Row) -> Article:
    return Article(
        article_id=row["article_id"],
        title=row["title"],
        content=row["content"],
        author_name=row["author_name"],
        author_email=row["author_email"],
        created_at=row["created_at"],
    )


def _delete_original(path: Path) -> None:
    root = (data_dir() / "originals").resolve()
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        return
    if resolved.is_file():
        resolved.unlink()
