"""SQLite database layer for bot domain entities."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.db.configs import SEED_PRODUCTS, SEED_REVIEWS


class Database:
    """Thin SQLite wrapper with app-specific CRUD operations."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("DATABASE_PATH", "fitness.db")
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
                    calculation_type TEXT,
                    calculation_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (diagnosis_session_id) REFERENCES diagnosis_sessions(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS user_diagnostic_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    first_name TEXT,
                    full_name TEXT,
                    sex TEXT,
                    age INTEGER,
                    height_cm REAL,
                    weight_kg REAL,
                    waist_cm REAL,
                    hips_cm REAL,
                    chest_cm REAL,
                    wrist_cm REAL,
                    sitting_height_cm REAL,
                    goal TEXT,
                    health_notes TEXT,
                    activity_level TEXT,
                    meals_count INTEGER,
                    known_fat_percent REAL,
                    contraindications_payload TEXT,
                    flexibility_payload TEXT,
                    caliper_payload TEXT,
                    latest_body_metrics_payload TEXT,
                    latest_calories_payload TEXT,
                    latest_report_text TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                table_name="calculations_history",
                column_name="calculation_type",
                column_sql="calculation_type TEXT",
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

    def save_calculation_history(
        self,
        user_id: int,
        calculation_type: str,
        payload: dict[str, Any],
        diagnosis_session_id: int | None = None,
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO calculations_history (user_id, diagnosis_session_id, calculation_type, calculation_payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    diagnosis_session_id,
                    calculation_type,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            return int(cursor.lastrowid)

    def upsert_diagnostic_profile(self, user: dict[str, Any], data: dict[str, Any]) -> None:
        with self.connection() as conn:
            merged = {**user, **data}
            conn.execute(
                """
                INSERT INTO user_diagnostic_profiles (
                    user_id, telegram_id, username, first_name, full_name, sex, age, height_cm, weight_kg,
                    waist_cm, hips_cm, chest_cm, wrist_cm, sitting_height_cm, goal, health_notes,
                    activity_level, meals_count, known_fat_percent, contraindications_payload, flexibility_payload,
                    caliper_payload, latest_body_metrics_payload, latest_calories_payload, latest_report_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    user_id=excluded.user_id,
                    username=excluded.username,
                    first_name=excluded.first_name,
                    full_name=excluded.full_name,
                    sex=COALESCE(excluded.sex, user_diagnostic_profiles.sex),
                    age=COALESCE(excluded.age, user_diagnostic_profiles.age),
                    height_cm=COALESCE(excluded.height_cm, user_diagnostic_profiles.height_cm),
                    weight_kg=COALESCE(excluded.weight_kg, user_diagnostic_profiles.weight_kg),
                    waist_cm=COALESCE(excluded.waist_cm, user_diagnostic_profiles.waist_cm),
                    hips_cm=COALESCE(excluded.hips_cm, user_diagnostic_profiles.hips_cm),
                    chest_cm=COALESCE(excluded.chest_cm, user_diagnostic_profiles.chest_cm),
                    wrist_cm=COALESCE(excluded.wrist_cm, user_diagnostic_profiles.wrist_cm),
                    sitting_height_cm=COALESCE(excluded.sitting_height_cm, user_diagnostic_profiles.sitting_height_cm),
                    goal=COALESCE(excluded.goal, user_diagnostic_profiles.goal),
                    health_notes=COALESCE(excluded.health_notes, user_diagnostic_profiles.health_notes),
                    activity_level=COALESCE(excluded.activity_level, user_diagnostic_profiles.activity_level),
                    meals_count=COALESCE(excluded.meals_count, user_diagnostic_profiles.meals_count),
                    known_fat_percent=COALESCE(excluded.known_fat_percent, user_diagnostic_profiles.known_fat_percent),
                    contraindications_payload=COALESCE(excluded.contraindications_payload, user_diagnostic_profiles.contraindications_payload),
                    flexibility_payload=COALESCE(excluded.flexibility_payload, user_diagnostic_profiles.flexibility_payload),
                    caliper_payload=COALESCE(excluded.caliper_payload, user_diagnostic_profiles.caliper_payload),
                    latest_body_metrics_payload=COALESCE(excluded.latest_body_metrics_payload, user_diagnostic_profiles.latest_body_metrics_payload),
                    latest_calories_payload=COALESCE(excluded.latest_calories_payload, user_diagnostic_profiles.latest_calories_payload),
                    latest_report_text=COALESCE(excluded.latest_report_text, user_diagnostic_profiles.latest_report_text),
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    merged.get("user_id"),
                    merged.get("telegram_id"),
                    merged.get("username"),
                    merged.get("first_name"),
                    merged.get("full_name"),
                    merged.get("sex"),
                    merged.get("age"),
                    merged.get("height_cm"),
                    merged.get("weight_kg"),
                    merged.get("waist_cm"),
                    merged.get("hips_cm"),
                    merged.get("chest_cm"),
                    merged.get("wrist_cm"),
                    merged.get("sitting_height_cm"),
                    merged.get("goal"),
                    merged.get("health_notes"),
                    merged.get("activity_level"),
                    merged.get("meals_count"),
                    merged.get("known_fat_percent"),
                    json.dumps(merged.get("contraindications_payload"), ensure_ascii=False) if merged.get("contraindications_payload") is not None else None,
                    json.dumps(merged.get("flexibility_payload"), ensure_ascii=False) if merged.get("flexibility_payload") is not None else None,
                    json.dumps(merged.get("caliper_payload"), ensure_ascii=False) if merged.get("caliper_payload") is not None else None,
                    json.dumps(merged.get("latest_body_metrics_payload"), ensure_ascii=False) if merged.get("latest_body_metrics_payload") is not None else None,
                    json.dumps(merged.get("latest_calories_payload"), ensure_ascii=False) if merged.get("latest_calories_payload") is not None else None,
                    merged.get("latest_report_text"),
                ),
            )

    def get_diagnostic_profile_by_telegram_id(self, telegram_id: int) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM user_diagnostic_profiles WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        for key in (
            "contraindications_payload",
            "flexibility_payload",
            "caliper_payload",
            "latest_body_metrics_payload",
            "latest_calories_payload",
        ):
            raw = result.get(key)
            result[key] = json.loads(raw) if isinstance(raw, str) and raw else None
        return result

    def get_latest_profile_or_none(self, telegram_id: int) -> dict[str, Any] | None:
        return self.get_diagnostic_profile_by_telegram_id(telegram_id)

    def update_diagnostic_profile_fields(self, telegram_id: int, fields: dict[str, Any]) -> None:
        if not fields:
            return
        encoded_fields: dict[str, Any] = {}
        for key, value in fields.items():
            if key.endswith("_payload") and value is not None and not isinstance(value, str):
                encoded_fields[key] = json.dumps(value, ensure_ascii=False)
            else:
                encoded_fields[key] = value
        set_clause = ", ".join(f"{field} = ?" for field in encoded_fields)
        values = list(encoded_fields.values()) + [telegram_id]
        with self.connection() as conn:
            conn.execute(
                f"UPDATE user_diagnostic_profiles SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?",
                values,
            )

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

    def mark_diagnosis_lead_sent(self, diagnosis_session_id: int) -> None:
        """Mark diagnosis lead as successfully sent."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE diagnosis_sessions
                SET lead_sent = 1
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

    def mark_payment_lead_sent(self, payment_id: int) -> None:
        """Mark payment lead as successfully sent."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE payments
                SET lead_sent = 1
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

    def mark_questionnaire_lead_sent(self, questionnaire_id: int) -> None:
        """Mark full questionnaire lead as successfully sent."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE questionnaire_answers
                SET lead_sent = 1
                WHERE id = ?
                """,
                (questionnaire_id,),
            )

    def get_unsent_diagnosis_leads(self) -> list[dict[str, Any]]:
        """Return diagnosis leads that were not delivered to admin."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    ds.id AS lead_id,
                    ds.user_id AS user_id,
                    ds.session_payload AS payload,
                    u.telegram_id AS telegram_user_id,
                    u.username AS telegram_username
                FROM diagnosis_sessions ds
                JOIN users u ON u.id = ds.user_id
                WHERE ds.lead_sent = 0
                ORDER BY ds.created_at ASC, ds.id ASC
                """
            ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            payload_raw = row["payload"]
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else {}
            result.append(
                {
                    "lead_id": int(row["lead_id"]),
                    "user_id": int(row["user_id"]),
                    "payload": payload,
                    "telegram_user_id": row["telegram_user_id"],
                    "telegram_username": row["telegram_username"],
                }
            )
        return result

    def get_unsent_questionnaire_leads(self) -> list[dict[str, Any]]:
        """Return questionnaire leads that were not delivered to admin."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    qa.id AS lead_id,
                    qa.user_id AS user_id,
                    qa.answers_payload AS payload,
                    u.telegram_id AS telegram_user_id,
                    u.username AS telegram_username
                FROM questionnaire_answers qa
                JOIN users u ON u.id = qa.user_id
                WHERE qa.lead_sent = 0
                ORDER BY qa.created_at ASC, qa.id ASC
                """
            ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            payload_raw = row["payload"]
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else {}
            result.append(
                {
                    "lead_id": int(row["lead_id"]),
                    "user_id": int(row["user_id"]),
                    "payload": payload,
                    "telegram_user_id": row["telegram_user_id"],
                    "telegram_username": row["telegram_username"],
                }
            )
        return result

    def get_unsent_payment_leads(self) -> list[dict[str, Any]]:
        """Return payment leads that were not delivered to admin."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.id AS payment_id,
                    p.user_id AS user_id,
                    p.amount AS amount,
                    p.payload AS payload
                FROM payments p
                WHERE p.lead_sent = 0
                ORDER BY p.created_at ASC, p.id ASC
                """
            ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            payload_raw = row["payload"]
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else {}
            result.append(
                {
                    "payment_id": int(row["payment_id"]),
                    "user_id": int(row["user_id"]),
                    "amount": int(row["amount"]),
                    "payload": payload,
                }
            )
        return result

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
