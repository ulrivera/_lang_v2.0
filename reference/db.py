# data/db.py
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from config.settings import DB_PATH
from data.models import Session, SessionItem, SRSItem, FineTuningLog, PassiveAudio

logger = logging.getLogger(__name__)

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    modality TEXT NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    summary TEXT,
    hook_next_session TEXT,
    red_error_count INTEGER DEFAULT 0,
    total_items INTEGER DEFAULT 0,
    romanization_active INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS session_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    item_type TEXT NOT NULL,
    form TEXT NOT NULL,
    correct INTEGER NOT NULL,
    error_type TEXT,
    recast_applied TEXT,
    error_form TEXT,
    correct_form TEXT,
    structure TEXT
);

CREATE TABLE IF NOT EXISTS srs_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    item TEXT NOT NULL,
    translation TEXT,
    item_type TEXT,
    ease_factor REAL DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    last_quality INTEGER,
    next_review TEXT,
    source TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS passive_audio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    source_module TEXT NOT NULL,
    file_path TEXT NOT NULL,
    items_targeted TEXT,
    duration_seconds INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS finetuning_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_item_id INTEGER REFERENCES session_items(id),
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    user_input TEXT NOT NULL,
    ideal_output TEXT NOT NULL,
    error_type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._connection.commit()
        logger.debug(f"Database connected: {self.db_path}")

    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Database disconnected")

    def _conn(self) -> sqlite3.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection

    # --- Sessions ---

    def create_session(self, session: Session) -> int:
        cursor = self._conn().execute(
            "INSERT INTO sessions (date, language, level, modality) VALUES (?, ?, ?, ?)",
            (session.date, session.language, session.level, session.modality)
        )
        self._conn().commit()
        return cursor.lastrowid

    def get_level_up_eligibility(self, language: str, level: str,
                                streak: int, threshold: float) -> bool:
        """Retorna True si el usuario califica para subir de nivel."""
        rows = self._conn().execute(
            """SELECT red_error_count, total_items FROM sessions
            WHERE language=? AND level=?
            ORDER BY created_at DESC LIMIT ?""",
            (language, level, streak)
        ).fetchall()

        if len(rows) < streak:
            return False

        for row in rows:
            if row["total_items"] == 0:
                return False
            red_ratio = row["red_error_count"] / row["total_items"]
            if red_ratio >= threshold:
                return False

        return True

    def close_session(self, session_id: int, duration: int,
                      summary: str, hook: str) -> None:
        self._conn().execute(
            """UPDATE sessions
               SET duration_seconds=?, summary=?, hook_next_session=?
               WHERE id=?""",
            (duration, summary, hook, session_id)
        )
        self._conn().commit()

    def get_last_session(self, language: str) -> Optional[sqlite3.Row]:
        return self._conn().execute(
            """SELECT * FROM sessions
               WHERE language=?
               ORDER BY created_at DESC LIMIT 1""",
            (language,)
        ).fetchone()

    # --- Session Items ---

    def add_session_item(self, item: SessionItem) -> int:
        cursor = self._conn().execute(
            """INSERT INTO session_items
               (session_id, item_type, form, correct, error_type, recast_applied)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (item.session_id, item.item_type, item.form,
             int(item.correct), item.error_type, item.recast_applied)
        )
        self._conn().commit()
        return cursor.lastrowid

    # --- SRS ---

    def add_srs_item(self, item: SRSItem) -> int:
        cursor = self._conn().execute(
            """INSERT INTO srs_items
               (language, level, item, translation, item_type,
                ease_factor, interval_days, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.language, item.level, item.item, item.translation,
             item.item_type, item.ease_factor, item.interval_days, item.source)
        )
        self._conn().commit()
        return cursor.lastrowid

    def get_due_srs_items(self, language: str, limit: int = 10) -> list:
        return self._conn().execute(
            """SELECT * FROM srs_items
               WHERE language=? AND (next_review IS NULL OR next_review <= date('now'))
               ORDER BY next_review ASC LIMIT ?""",
            (language, limit)
        ).fetchall()

    def update_srs_item(self, item_id: int, ease_factor: float,
                        interval_days: int, quality: int, next_review: str) -> None:
        self._conn().execute(
            """UPDATE srs_items
               SET ease_factor=?, interval_days=?, last_quality=?, next_review=?
               WHERE id=?""",
            (ease_factor, interval_days, quality, next_review, item_id)
        )
        self._conn().commit()

    # --- Fine-tuning log ---

    def add_finetuning_log(self, log: FineTuningLog) -> int:
        cursor = self._conn().execute(
            """INSERT INTO finetuning_log
               (session_item_id, language, level, user_input, ideal_output, error_type)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (log.session_item_id, log.language, log.level,
             log.user_input, log.ideal_output, log.error_type)
        )
        self._conn().commit()
        return cursor.lastrowid