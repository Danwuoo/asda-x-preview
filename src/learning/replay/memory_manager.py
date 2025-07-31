from __future__ import annotations

"""Persistence layer for replay entries."""

import json
import sqlite3
from contextlib import contextmanager
from typing import Iterator, List, Optional

from .replay_schema import ReplayEntry


class ReplayMemoryManager:
    """Store and retrieve :class:`ReplayEntry` objects."""

    def __init__(self, db_path: str = "data/replay/replay.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS replay_entries (
                replay_id TEXT PRIMARY KEY,
                data TEXT
            )"""
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def save_entry(self, entry: ReplayEntry) -> None:
        """Insert or update a replay entry."""
        data = entry.model_dump_json()
        self.conn.execute(
            "INSERT OR REPLACE INTO replay_entries (replay_id, data) VALUES (?, ?)",
            (entry.replay_id, data),
        )
        self.conn.commit()

    def load_entry(self, replay_id: str) -> ReplayEntry:
        """Fetch a single entry by id."""
        cur = self.conn.execute(
            "SELECT data FROM replay_entries WHERE replay_id=?", (replay_id,)
        )
        row = cur.fetchone()
        if not row:
            raise KeyError(replay_id)
        return ReplayEntry.model_validate(json.loads(row[0]))

    def query_entries(self, *, replay_label: Optional[str] = None) -> List[ReplayEntry]:
        """Retrieve entries optionally filtered by label."""
        cur = self.conn.execute("SELECT data FROM replay_entries")
        rows = [ReplayEntry.model_validate(json.loads(r[0])) for r in cur.fetchall()]
        if replay_label is not None:
            rows = [r for r in rows if r.replay_label == replay_label]
        return rows

    @contextmanager
    def session(self) -> Iterator["ReplayMemoryManager"]:
        try:
            yield self
        finally:
            self.close()


__all__ = ["ReplayMemoryManager"]
