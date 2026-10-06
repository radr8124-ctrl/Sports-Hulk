from pathlib import Path
from datetime import datetime, timezone
import sqlite3


ROOT = Path("/home/ubuntu/sports-hulk")
DB_PATH = ROOT / "data" / "sports_members.sqlite3"


def connect():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def ensure_schema():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS members (
                member_id TEXT PRIMARY KEY,
                email TEXT,
                phone_e164 TEXT,

                email_verified INTEGER NOT NULL DEFAULT 0,
                phone_verified INTEGER NOT NULL DEFAULT 0,

                status TEXT NOT NULL DEFAULT 'PENDING',
                plan TEXT NOT NULL DEFAULT 'FREE',

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS member_sports (
                member_id TEXT NOT NULL,
                sport TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,

                PRIMARY KEY (
                    member_id,
                    sport
                )
            );


            CREATE TABLE IF NOT EXISTS member_teams (
                member_id TEXT NOT NULL,
                sport TEXT NOT NULL,
                team TEXT NOT NULL,

                PRIMARY KEY (
                    member_id,
                    sport,
                    team
                )
            );


            CREATE TABLE IF NOT EXISTS member_players (
                member_id TEXT NOT NULL,
                sport TEXT NOT NULL,
                player TEXT NOT NULL,

                PRIMARY KEY (
                    member_id,
                    sport,
                    player
                )
            );


            CREATE TABLE IF NOT EXISTS notification_preferences (
                member_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,

                email_enabled INTEGER NOT NULL DEFAULT 0,
                sms_enabled INTEGER NOT NULL DEFAULT 0,

                frequency TEXT NOT NULL DEFAULT 'INSTANT',

                quiet_hours_enabled INTEGER NOT NULL DEFAULT 0,
                quiet_start TEXT,
                quiet_end TEXT,

                updated_at TEXT NOT NULL,

                PRIMARY KEY (
                    member_id,
                    alert_type
                )
            );


            CREATE TABLE IF NOT EXISTS consent_events (
                consent_id INTEGER PRIMARY KEY AUTOINCREMENT,

                member_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                event_type TEXT NOT NULL,

                source TEXT,
                consent_text_version TEXT,

                created_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS notification_delivery_log (
                delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,

                member_id TEXT NOT NULL,

                channel TEXT NOT NULL,
                alert_type TEXT NOT NULL,

                destination_hash TEXT,

                status TEXT NOT NULL,

                provider_message_id TEXT,

                created_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS notification_suppression (
                member_id TEXT NOT NULL,
                channel TEXT NOT NULL,

                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,

                PRIMARY KEY (
                    member_id,
                    channel
                )
            );


            CREATE INDEX IF NOT EXISTS idx_members_email
                ON members(email);

            CREATE INDEX IF NOT EXISTS idx_members_phone
                ON members(phone_e164);

            CREATE INDEX IF NOT EXISTS idx_delivery_member
                ON notification_delivery_log(member_id);

            CREATE INDEX IF NOT EXISTS idx_delivery_created
                ON notification_delivery_log(created_at);
            """
        )


def schema_status():
    ensure_schema()

    with connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                """
            )
        }

    return tables


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()
