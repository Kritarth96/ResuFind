import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATABASE_PATH = Path(os.getenv("RESUFIND_DB_PATH", Path(__file__).with_name("resufind.db")))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS saved_jobs (
                user_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                job_json TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                PRIMARY KEY (user_id, job_id)
            );
            CREATE TABLE IF NOT EXISTS alert_preferences (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                cadence TEXT NOT NULL,
                profile_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def save_job(user_id: str, job: dict) -> dict:
    saved_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO saved_jobs (user_id, job_id, job_json, saved_at) VALUES (?, ?, ?, ?)",
            (user_id, job["id"], json.dumps(job), saved_at),
        )
    return {"user_id": user_id, "job": job, "saved_at": saved_at}


def list_saved_jobs(user_id: str) -> list[dict]:
    with connect() as connection:
        rows = connection.execute("SELECT job_json, saved_at FROM saved_jobs WHERE user_id = ? ORDER BY saved_at DESC", (user_id,)).fetchall()
    return [{"job": json.loads(row["job_json"]), "saved_at": row["saved_at"]} for row in rows]


def remove_saved_job(user_id: str, job_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?", (user_id, job_id))
    return cursor.rowcount > 0


def save_alert(user_id: str, email: str, cadence: str, profile: dict) -> dict:
    updated_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO alert_preferences (user_id, email, cadence, profile_json, updated_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, cadence, json.dumps(profile), updated_at),
        )
    return {"user_id": user_id, "email": email, "cadence": cadence, "profile": profile, "updated_at": updated_at}


def get_alert(user_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute("SELECT email, cadence, profile_json, updated_at FROM alert_preferences WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    return {"user_id": user_id, "email": row["email"], "cadence": row["cadence"], "profile": json.loads(row["profile_json"]), "updated_at": row["updated_at"]}
