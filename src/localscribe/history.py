from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .domain import CleanupMode, Transcript


@dataclass(frozen=True)
class HistoryEntry:
    entry_id: int
    created_at: str
    raw: str
    cleaned: str
    language: str
    duration_seconds: float
    mode: CleanupMode


class TranscriptHistory:
    """Small local SQLite transcript archive; no audio or network access."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                raw TEXT NOT NULL,
                cleaned TEXT NOT NULL,
                language TEXT NOT NULL,
                duration_seconds REAL NOT NULL,
                mode TEXT NOT NULL
            )
            """
        )
        return connection

    def add(self, transcript: Transcript) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO transcripts
                    (created_at, raw, cleaned, language, duration_seconds, mode)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    transcript.raw,
                    transcript.cleaned,
                    transcript.language,
                    transcript.duration_seconds,
                    transcript.mode.value,
                ),
            )
            if cursor.lastrowid is None:
                raise sqlite3.DatabaseError("Transcript history insert did not return an ID")
            return cursor.lastrowid

    def search(self, query: str = "", limit: int = 200) -> list[HistoryEntry]:
        escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, raw, cleaned, language, duration_seconds, mode
                FROM transcripts
                WHERE ? = '' OR raw LIKE ? ESCAPE '\\' OR cleaned LIKE ? ESCAPE '\\'
                ORDER BY id DESC
                LIMIT ?
                """,
                (query.strip(), pattern, pattern, max(1, min(limit, 1000))),
            ).fetchall()
        return [
            HistoryEntry(
                entry_id=int(row[0]),
                created_at=str(row[1]),
                raw=str(row[2]),
                cleaned=str(row[3]),
                language=str(row[4]),
                duration_seconds=float(row[5]),
                mode=CleanupMode(str(row[6])),
            )
            for row in rows
        ]

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM transcripts")
