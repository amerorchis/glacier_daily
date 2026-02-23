"""Last Known Good (LKG) cache for module outputs.

Stores the most recent successful output of each data module so that
when an API fails, the system can fall back to the previous good data
instead of returning empty strings.

Two caching behaviors are supported:

- **Date-deterministic modules** (peak, image_otd, product): result is
  fixed by today's date seed. LKG acts as a primary cache — checked
  before the API call, skipping the module entirely if today's data exists.

- **Dynamic modules** (weather, roads, etc.): always attempt a fresh
  fetch. LKG is only a fallback when the API call fails.

All data is same-day only (Mountain Time). If the saved date doesn't
match today, ``load()`` returns ``None``.

Thread-safe: uses SQLite in WAL mode with ``check_same_thread=False``.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import threading

from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = ".lkg_cache.db"


class LKGCache:
    """Singleton SQLite-backed cache for last known good module outputs."""

    _instance: LKGCache | None = None
    _lock = threading.Lock()

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._db_path = db_path
        try:
            self._conn = sqlite3.connect(
                db_path,
                check_same_thread=False,
                isolation_level="DEFERRED",
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lkg_data (
                    module_name TEXT NOT NULL,
                    field_key   TEXT NOT NULL,
                    value       TEXT NOT NULL,
                    saved_date  TEXT NOT NULL,
                    PRIMARY KEY (module_name, field_key)
                )
                """
            )
            self._conn.commit()
        except sqlite3.DatabaseError:
            logger.warning("LKG cache corrupt, recreating")
            self._conn.close()
            os.remove(db_path)
            self._conn = sqlite3.connect(
                db_path,
                check_same_thread=False,
                isolation_level="DEFERRED",
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lkg_data (
                    module_name TEXT NOT NULL,
                    field_key   TEXT NOT NULL,
                    value       TEXT NOT NULL,
                    saved_date  TEXT NOT NULL,
                    PRIMARY KEY (module_name, field_key)
                )
                """
            )
            self._conn.commit()

    @classmethod
    def get_cache(cls) -> LKGCache:
        """Get or create the singleton LKGCache instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=DB_PATH)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Close and discard the singleton. For tests."""
        with cls._lock:
            if cls._instance is not None:
                with contextlib.suppress(sqlite3.Error):
                    cls._instance._conn.close()
                cls._instance = None

    def save(self, module_name: str, data: dict[str, str]) -> None:
        """Save successful module output to the LKG cache.

        Stores each key-value pair with today's date (Mountain Time).
        Overwrites any existing data for the same module/key.
        """
        today = now_mountain().strftime("%Y-%m-%d")
        with self._lock:
            for key, value in data.items():
                self._conn.execute(
                    """INSERT OR REPLACE INTO lkg_data
                       (module_name, field_key, value, saved_date)
                       VALUES (?, ?, ?, ?)""",
                    (module_name, key, value, today),
                )
            self._conn.commit()

    def load(self, module_name: str, keys: list[str]) -> dict[str, str] | None:
        """Load today's LKG data for a module.

        Returns a dict mapping field keys to values if ALL requested keys
        have data from today. Returns ``None`` if any key is missing or
        if the data is from a different day.
        """
        today = now_mountain().strftime("%Y-%m-%d")
        results: dict[str, str] = {}
        for key in keys:
            row = self._conn.execute(
                """SELECT value, saved_date FROM lkg_data
                   WHERE module_name = ? AND field_key = ?""",
                (module_name, key),
            ).fetchone()
            if row is None or row[1] != today:
                return None
            results[key] = row[0]
        return results

    def clear_modules(self, module_names: list[str]) -> None:
        """Remove cached data for specific modules.

        Used by ``--force`` to clear date-deterministic modules so they
        are re-fetched.
        """
        with self._lock:
            for name in module_names:
                self._conn.execute(
                    "DELETE FROM lkg_data WHERE module_name = ?", (name,)
                )
            self._conn.commit()
