"""
Local, opt-in storage for professional override logs (SDLC Phase 6.1).

On-device only. Never transmitted automatically. Export is always a
separate, explicit, manual action (export_logs_to_file below) — never
triggered by simply logging an override.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS override_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    category TEXT NOT NULL,
    rule_classification TEXT NOT NULL,
    rule_action_level INTEGER NOT NULL,
    professional_decision TEXT NOT NULL,
    note TEXT
);
"""


class LocalStore:
    def __init__(self, db_path: Path | None = None, enabled: bool | None = None):
        self.db_path = db_path or config.STORAGE_DB_PATH
        self.enabled = (
            config.OVERRIDE_LOGGING_ENABLED_DEFAULT if enabled is None else enabled
        )

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(_SCHEMA)
        return conn

    def log_override(
        self,
        category: str,
        rule_classification: str,
        rule_action_level: int,
        professional_decision: str,
        note: str = "",
    ) -> bool:
        """Logs a case where the professional's decision differed from
        the rules engine's classification/action. No-op (returns False)
        unless the user has explicitly opted in — this must never log
        silently."""
        if not self.enabled:
            return False
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO override_log "
                "(timestamp_utc, category, rule_classification, "
                "rule_action_level, professional_decision, note) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    category,
                    rule_classification,
                    rule_action_level,
                    professional_decision,
                    note,
                ),
            )
        return True

    def export_logs_to_file(self, output_path: str) -> str:
        """The ONLY way logs leave the device — an explicit, manual call
        the user must trigger themselves (e.g. clicking an "Export
        logs" button in the UI). Never called automatically."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT timestamp_utc, category, rule_classification, "
                "rule_action_level, professional_decision, note "
                "FROM override_log ORDER BY timestamp_utc"
            ).fetchall()

        records = [
            {
                "timestamp_utc": r[0],
                "category": r[1],
                "rule_classification": r[2],
                "rule_action_level": r[3],
                "professional_decision": r[4],
                "note": r[5],
            }
            for r in rows
        ]
        with open(output_path, "w") as f:
            json.dump(records, f, indent=2)
        return output_path