"""SQLite database layer for bot domain entities."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.db.configs import SEED_PRODUCTS, SEED_REVIEWS


class Database:
    """Thin SQLite wrapper with app-specific CRUD operations."""

    def __init__(self, db_path: str = "fitness.db") -> None:
        self.db_path = db_path
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        db_file = Path(self.db_path)
        if db_file.parent != Path("."):
            db_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create required schema and seed static tables."""
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS diagnosis_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_payload TEXT NOT NULL,
                    user_report_text TEXT,
                    admin_report_text TEXT,
                    lead_sent INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS questionnaire_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    diagnosis_session_id INTEGER,
                    answers_payload TEXT NOT NULL,
                    lead_sent INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (diagnosis_session_id) REFERENCES diagnosis_sessions(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS calculations_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    diagnosis_session_id INTEGER,
                    calculation_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (diagnosis_session_id) REFERENCES diagnosis_sessions(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    provider_payment_id TEXT,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL,
                    lead_sent INTEGER NOT NULL DEFAULT 1,
                    payload TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author_name TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    is_published INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(author_name, text)
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT,
                    price INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_column(
                conn=conn,
                table_name="diagnosis_sessions",
                column_name="lead_sent",
                column_sql="lead_sent INTEGER NOT NULL DEFAULT 1",
            )
            self._ensure_column(
                conn=conn,
                table_name="diagnosis_sessions",
                column_name="user_report_text",
                column_sql="user_report_text TEXT",
            )
            self._ensure_column(
                conn=conn,
                table_name="diagnosis_sessions",
                column_name="admin_report_text",
                column_sql="admin_report_text TEXT",
            )
            self._ensure_column(
                conn=conn,
                table_name="questionnaire_answers",
                column_name="lead_sent",
                column_sql="lead_sent INTEGER NOT NULL DEFAULT 1",
            )
            self._ensure_column(
                conn=conn,
                table_name="payments",
                column_name="lead_sent",
                column_sql="lead_sent INTEGER NOT NULL DEFAULT 1",
            )
            self._seed_products(conn)
            self._seed_reviews(conn)

    def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> int:
        """Insert or update user and return internal user id."""
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_id, username, first_name, last_name),
            )
            row = conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("Failed to upsert user")
            return int(row["id"])

    def save_diagnosis_session_and_calculation(
        self,
        user_id: int,
        session_payload: dict[str, Any],
        calculation_payload: dict[str, Any],
        user_report_text: str | None = None,
        admin_report_text: str | None = None,
        lead_sent: bool = True,
    ) -> int:
        """Persist diagnosis session and related calculation. Return session id."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO diagnosis_sessions (
                    user_id,
                    session_payload,
                    user_report_text,
                    admin_report_text,
                    lead_sent
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    json.dumps(session_payload, ensure_ascii=False),
                    user_report_text,
                    admin_report_text,
                    int(lead_sent),
                ),
            )
            diagnosis_session_id = int(cursor.lastrowid)
            conn.execute(
                """
                INSERT INTO calculations_history (user_id, diagnosis_session_id, calculation_payload)
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    diagnosis_session_id,
                    json.dumps(calculation_payload, ensure_ascii=False),
                ),
            )
            return diagnosis_session_id

    def get_latest_diagnosis_result(self, user_id: int) -> dict[str, Any] | None:
        """Return latest diagnosis session with related calculation payload."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    ds.id AS diagnosis_session_id,
                    ds.session_payload AS session_payload,
                    ds.user_report_text AS user_report_text,
                    ds.admin_report_text AS admin_report_text,
                    ds.created_at AS session_created_at,
                    ch.calculation_payload AS calculation_payload,
                    ch.created_at AS calculation_created_at
                FROM diagnosis_sessions ds
                LEFT JOIN calculations_history ch
                    ON ch.diagnosis_session_id = ds.id
                WHERE ds.user_id = ?
                ORDER BY ds.created_at DESC, ds.id DESC, ch.created_at DESC, ch.id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                return None

            session_payload_raw = row["session_payload"]
            calculation_payload_raw = row["calculation_payload"]
            session_payload = (
                json.loads(session_payload_raw)
                if isinstance(session_payload_raw, str)
                else {}
            )
            calculation_payload = (
                json.loads(calculation_payload_raw)
                if isinstance(calculation_payload_raw, str)
                else {}
            )
            return {
                "diagnosis_session_id": int(row["diagnosis_session_id"]),
                "session_payload": session_payload,
                "user_report_text": row["user_report_text"],
                "admin_report_text": row["admin_report_text"],
                "session_created_at": row["session_created_at"],
                "calculation_payload": calculation_payload,
                "calculation_created_at": row["calculation_created_at"],
            }

    def save_full_questionnaire(
        self,
        user_id: int,
        answers_payload: dict[str, Any],
        diagnosis_session_id: int | None = None,
        lead_sent: bool = True,
    ) -> int:
        """Persist full questionnaire answers. Return questionnaire record id."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO questionnaire_answers (
                    user_id,
                    diagnosis_session_id,
                    answers_payload,
                    lead_sent
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    diagnosis_session_id,
                    json.dumps(answers_payload, ensure_ascii=False),
                    int(lead_sent),
                ),
            )
            return int(cursor.lastrowid)

    def record_payment(
        self,
        user_id: int,
        amount: int,
        currency: str,
        status: str,
        provider_payment_id: str | None = None,
        payload: dict[str, Any] | None = None,
        lead_sent: bool = True,
    ) -> int:
        """Persist payment event and return payment record id."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO payments (
                    user_id,
                    provider_payment_id,
                    amount,
                    currency,
                    status,
                    lead_sent,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    provider_payment_id,
                    amount,
                    currency,
                    status,
                    int(lead_sent),
                    json.dumps(payload, ensure_ascii=False) if payload else None,
                ),
            )
            return int(cursor.lastrowid)

    def mark_diagnosis_lead_unsent(self, diagnosis_session_id: int) -> None:
        """Mark diagnosis lead as not sent for retries."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE diagnosis_sessions
                SET lead_sent = 0
                WHERE id = ?
                """,
                (diagnosis_session_id,),
            )

    def mark_payment_lead_unsent(self, payment_id: int) -> None:
        """Mark payment lead as not sent for retries."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE payments
                SET lead_sent = 0
                WHERE id = ?
                """,
                (payment_id,),
            )

    def mark_questionnaire_lead_unsent(self, questionnaire_id: int) -> None:
        """Mark full questionnaire lead as not sent for retries."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE questionnaire_answers
                SET lead_sent = 0
                WHERE id = ?
                """,
                (questionnaire_id,),
            )

    def _seed_products(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO products (code, name, description, price, currency, is_active)
            VALUES (:code, :name, :description, :price, :currency, :is_active)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                price = excluded.price,
                currency = excluded.currency,
                is_active = excluded.is_active
            """,
            SEED_PRODUCTS,
        )

    def _seed_reviews(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO reviews (author_name, rating, text, is_published)
            VALUES (:author_name, :rating, :text, :is_published)
            ON CONFLICT(author_name, text) DO UPDATE SET
                rating = excluded.rating,
                is_published = excluded.is_published
            """,
            SEED_REVIEWS,
        )

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_sql: str,
    ) -> None:
        """Add missing column for backward-compatible migrations."""
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing_columns = {str(row["name"]) for row in rows}
        if column_name in existing_columns:
            return
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
