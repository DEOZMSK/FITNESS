"""Analytics event logging and daily reporting."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import Bot

from app.config import Settings
from app.db import Database
from app.services.admin_notify import get_admin_recipients

logger = logging.getLogger(__name__)

_FUNNEL_EVENTS = (
    "start",
    "about_open",
    "services_open",
    "diagnostics_start",
    "diagnostics_complete",
    "donate_start",
    "payment_success",
)


def _connection(database_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_events_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            telegram_id INTEGER,
            user_id INTEGER,
            meta_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _safe_parse_meta(meta_json: str | None) -> dict[str, Any] | None:
    if not meta_json:
        return None
    try:
        parsed = json.loads(meta_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def log_event(
    event_name: str,
    telegram_id: int | None = None,
    user_id: int | None = None,
    meta: dict | None = None,
) -> None:
    """Persist a single analytics event in SQLite."""
    from app.config import load_settings

    settings = load_settings()
    serialized_meta = None
    if meta is not None:
        serialized_meta = json.dumps(meta, ensure_ascii=False)

    with _connection(settings.database_path) as conn:
        _ensure_events_table(conn)
        conn.execute(
            """
            INSERT INTO analytics_events (event_name, telegram_id, user_id, meta_json)
            VALUES (?, ?, ?, ?)
            """,
            (event_name, telegram_id, user_id, serialized_meta),
        )
        conn.commit()


def get_event_stats_for_period(start_dt: datetime, end_dt: datetime) -> dict[str, Any]:
    """Aggregate analytics data for the requested UTC datetime period."""
    from app.config import load_settings

    settings = load_settings()
    start_utc = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

    with _connection(settings.database_path) as conn:
        _ensure_events_table(conn)
        rows = conn.execute(
            """
            SELECT event_name, telegram_id, user_id, meta_json, created_at
            FROM analytics_events
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at ASC
            """,
            (
                start_utc.strftime("%Y-%m-%d %H:%M:%S"),
                end_utc.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ).fetchall()

    unique_users: set[str] = set()
    events_counter: Counter[str] = Counter()

    for row in rows:
        telegram_id = row["telegram_id"]
        user_id = row["user_id"]
        if telegram_id is not None:
            unique_users.add(f"tg:{telegram_id}")
        elif user_id is not None:
            unique_users.add(f"usr:{user_id}")

        events_counter[row["event_name"]] += 1
        _safe_parse_meta(row["meta_json"])

    return {
        "total_events": len(rows),
        "unique_users": len(unique_users),
        "event_counts": dict(events_counter),
    }


def build_daily_report_text(report_date: date, stats: dict[str, Any]) -> str:
    """Build a human-readable daily analytics report."""
    total_events = int(stats.get("total_events", 0) or 0)
    if total_events == 0:
        return "Активности за день не было."

    unique_users = int(stats.get("unique_users", 0) or 0)
    event_counts: dict[str, int] = stats.get("event_counts", {}) or {}

    start_count = int(event_counts.get("start", 0) or 0)

    def conv_line(event_key: str, label: str) -> str:
        value = int(event_counts.get(event_key, 0) or 0)
        percent = (value / start_count * 100) if start_count else 0.0
        return f"• {label}: {value}/{start_count} ({percent:.1f}%)"

    lines = [
        "📊 Ежедневный отчёт по активности",
        f"Дата: {report_date.strftime('%Y-%m-%d')}",
        "",
        "👥 Пользователи и события",
        f"• Уникальные пользователи: {unique_users}",
        f"• Всего событий: {total_events}",
        "",
        "🧭 Воронка",
    ]
    lines.extend(f"• {event}: {int(event_counts.get(event, 0) or 0)}" for event in _FUNNEL_EVENTS)
    lines.extend(
        [
            "",
            "📈 Конверсии от start",
            conv_line("diagnostics_complete", "diagnostics_complete/start"),
            conv_line("services_open", "services_open/start"),
            conv_line("payment_success", "payment_success/start"),
            "",
            "🗂 Все события",
        ]
    )

    for event_name in sorted(event_counts):
        lines.append(f"• {event_name}: {int(event_counts[event_name] or 0)}")

    return "\n".join(lines)


async def send_yesterday_report_if_due(bot: Bot, settings: Settings) -> None:
    """Send yesterday's report after the configured local daily-report time."""
    local_tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(local_tz)
    scheduled_local = now_local.replace(
        hour=settings.daily_report_hour,
        minute=settings.daily_report_minute,
        second=0,
        microsecond=0,
    )
    if now_local < scheduled_local:
        return

    report_date_local = now_local.date() - timedelta(days=1)
    start_local = datetime.combine(report_date_local, time.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)

    stats = get_event_stats_for_period(
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )
    text = build_daily_report_text(report_date_local, stats)
    report_date_key = report_date_local.isoformat()
    db = Database()
    delivery_errors: list[int] = []

    for admin_id in get_admin_recipients():
        if db.has_daily_report_been_sent(report_date_key, admin_id):
            continue
        try:
            await bot.send_message(admin_id, text)
            db.mark_daily_report_sent(report_date_key, admin_id)
        except Exception:
            delivery_errors.append(admin_id)
            logger.exception(
                "Failed to send daily analytics report report_date=%s admin_id=%s",
                report_date_key,
                admin_id,
            )

    if delivery_errors:
        raise RuntimeError(
            f"Failed daily report delivery for admin recipients: {delivery_errors}"
        )


async def daily_reports_worker(bot: Bot, settings: Settings) -> None:
    """Background worker that checks whether yesterday report should be sent."""
    last_sent_for_date: date | None = None

    while True:
        local_tz = ZoneInfo(settings.timezone)
        now_local = datetime.now(local_tz)
        report_date_local = now_local.date() - timedelta(days=1)
        scheduled_local = now_local.replace(
            hour=settings.daily_report_hour,
            minute=settings.daily_report_minute,
            second=0,
            microsecond=0,
        )

        if now_local >= scheduled_local and last_sent_for_date != report_date_local:
            try:
                await send_yesterday_report_if_due(bot, settings)
                last_sent_for_date = report_date_local
            except Exception:
                logger.exception("Failed to send yesterday analytics report")

        await asyncio.sleep(settings.report_check_interval_seconds)
