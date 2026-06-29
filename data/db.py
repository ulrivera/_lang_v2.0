# data/db.py
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from config.settings import DB_PATH
from data.models import (
    UserProfile, Session, SessionItem, LoraTrainingCandidate, VaultCard
)

logger = logging.getLogger(__name__)

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_l1 TEXT NOT NULL,
    current_level TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    modality TEXT NOT NULL,
    user_l1 TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS lora_training_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    module TEXT NOT NULL,
    full_prompt TEXT NOT NULL,
    raw_output TEXT NOT NULL,
    parsed_successfully INTEGER NOT NULL,
    validated_output TEXT,
    validation_source TEXT,
    used_for_training INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vault_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    level TEXT NOT NULL,
    card_type TEXT NOT NULL,
    tema TEXT,
    source_path TEXT NOT NULL,
    chroma_id TEXT NOT NULL UNIQUE,
    indexed_at TEXT DEFAULT (datetime('now'))
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

    def _conn(self) -> sqlite3.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected.")
        return self._connection

    # --- User Profile ---

    def get_or_create_profile(self, user_l1: str, default_level: str = "A0") -> sqlite3.Row:
        existing = self._conn().execute("SELECT * FROM user_profile LIMIT 1").fetchone()
        if existing:
            return existing
        self._conn().execute(
            "INSERT INTO user_profile (user_l1, current_level) VALUES (?, ?)",
            (user_l1, default_level)
        )
        self._conn().commit()
        return self._conn().execute("SELECT * FROM user_profile LIMIT 1").fetchone()

    def update_level(self, new_level: str) -> None:
        self._conn().execute("UPDATE user_profile SET current_level=?", (new_level,))
        self._conn().commit()

    # --- Sessions ---

    def create_session(self, session: Session) -> int:
        cursor = self._conn().execute(
            """INSERT INTO sessions (date, language, level, modality, user_l1)
               VALUES (?, ?, ?, ?, ?)""",
            (session.date, session.language, session.level, session.modality, session.user_l1)
        )
        self._conn().commit()
        return cursor.lastrowid

    def close_session(self, session_id: int, duration: int, summary: str, hook: str) -> None:
        self._conn().execute(
            """UPDATE sessions SET duration_seconds=?, summary=?, hook_next_session=?
               WHERE id=?""",
            (duration, summary, hook, session_id)
        )
        self._conn().commit()

    def get_last_session(self, language: str) -> Optional[sqlite3.Row]:
        return self._conn().execute(
            "SELECT * FROM sessions WHERE language=? ORDER BY created_at DESC LIMIT 1",
            (language,)
        ).fetchone()

    # --- LoRA training data ---

    def log_lora_candidate(self, candidate: LoraTrainingCandidate) -> int:
        cursor = self._conn().execute(
            """INSERT INTO lora_training_candidates
               (module, full_prompt, raw_output, parsed_successfully, validated_output, validation_source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (candidate.module, candidate.full_prompt, candidate.raw_output,
             int(candidate.parsed_successfully), candidate.validated_output, candidate.validation_source)
        )
        self._conn().commit()
        return cursor.lastrowid

    def count_lora_candidates(self, only_successful: bool = True) -> int:
        query = "SELECT COUNT(*) as c FROM lora_training_candidates"
        if only_successful:
            query += " WHERE parsed_successfully=1"
        return self._conn().execute(query).fetchone()["c"]

    # --- Vault cards ---

    def register_vault_card(self, card: VaultCard) -> int:
        cursor = self._conn().execute(
            """INSERT INTO vault_cards (language, level, card_type, tema, source_path, chroma_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (card.language, card.level, card.card_type, card.tema, card.source_path, card.chroma_id)
        )
        self._conn().commit()
        return cursor.lastrowid

    def get_cards_by_language(self, language: str) -> list:
        return self._conn().execute(
            "SELECT * FROM vault_cards WHERE language=?", (language,)
        ).fetchall()