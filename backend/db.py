"""
Crisis Command — SQLite Persistence Layer

Tables:
  incidents, units, state_versions, plans, assignments,
  plan_comparisons, resilience_results, action_log, events
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from backend.state import CrisisState

DB_PATH = Path(__file__).parent.parent / "crisis_command.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
    """Create tables if they don't exist."""
    if conn is None:
        conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS state_versions (
            version INTEGER PRIMARY KEY,
            state_json TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            version INTEGER,
            agent TEXT,
            action TEXT,
            details TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            type TEXT,
            target_id TEXT,
            description TEXT,
            timestamp TEXT
        );
    """)
    conn.commit()
    return conn


def save_state(state: CrisisState, conn: Optional[sqlite3.Connection] = None) -> None:
    """Persist a state snapshot."""
    if conn is None:
        conn = get_connection()
        init_db(conn)
    conn.execute(
        "INSERT OR REPLACE INTO state_versions (version, state_json) VALUES (?, ?)",
        (state.version, state.model_dump_json()),
    )
    for entry in state.action_log:
        conn.execute(
            "INSERT OR IGNORE INTO action_log (timestamp, version, agent, action, details) VALUES (?, ?, ?, ?, ?)",
            (entry.timestamp, entry.version, entry.agent, entry.action, entry.details),
        )
    for event in state.system_events:
        conn.execute(
            "INSERT OR REPLACE INTO events (id, type, target_id, description, timestamp) VALUES (?, ?, ?, ?, ?)",
            (event.id, event.type, event.target_id, event.description, event.timestamp),
        )
    conn.commit()


def load_latest_state(conn: Optional[sqlite3.Connection] = None) -> Optional[CrisisState]:
    """Load the latest state from DB."""
    if conn is None:
        conn = get_connection()
        init_db(conn)
    row = conn.execute(
        "SELECT state_json FROM state_versions ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row:
        return CrisisState.model_validate_json(row["state_json"])
    return None
