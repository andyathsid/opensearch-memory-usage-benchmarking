from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .errors import HarvestError


class MetadataStore:
    """SQLite-backed record and resume state store."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                global_id TEXT PRIMARY KEY,
                record_json TEXT NOT NULL,
                harvested_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> MetadataStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def ensure_source(self, base_url: str, subtree: str) -> None:
        expected = {"base_url": base_url.rstrip("/"), "subtree": subtree}
        existing = self.get_state("source")
        if existing is None:
            self.set_state("source", json.dumps(expected, sort_keys=True))
            return
        if json.loads(existing) != expected:
            raise HarvestError(
                "The output database belongs to a different Dataverse source. "
                "Choose another --output-dir."
            )

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM records").fetchone()
        return int(row[0])

    def get_state(self, key: str) -> str | None:
        row = self.connection.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def get_int_state(self, key: str, default: int = 0) -> int:
        value = self.get_state(key)
        return default if value is None else int(value)

    def get_bool_state(self, key: str, default: bool = False) -> bool:
        value = self.get_state(key)
        return default if value is None else value == "true"

    def set_state(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO state(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def save_page(
        self,
        items: Iterable[dict[str, Any]],
        next_start: int,
        repository_total: int,
        catalog_complete: bool,
    ) -> None:
        harvested_at = datetime.now(UTC).isoformat()
        prepared_records: list[tuple[str, str, str]] = []
        for item in items:
            global_id = item.get("global_id")
            if not isinstance(global_id, str) or not global_id.strip():
                raise HarvestError("A dataset record is missing its global_id")
            prepared_records.append(
                (
                    global_id,
                    json.dumps(item, ensure_ascii=False, separators=(",", ":")),
                    harvested_at,
                )
            )

        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO records(global_id, record_json, harvested_at) VALUES (?, ?, ?)
                ON CONFLICT(global_id) DO UPDATE SET
                    record_json = excluded.record_json,
                    harvested_at = excluded.harvested_at
                """,
                prepared_records,
            )
            state_values = {
                "next_start": str(next_start),
                "repository_total": str(repository_total),
                "catalog_complete": "true" if catalog_complete else "false",
                "last_harvested_at": harvested_at,
            }
            self.connection.executemany(
                """
                INSERT INTO state(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                state_values.items(),
            )

    def records(self) -> Iterable[dict[str, Any]]:
        cursor = self.connection.execute("SELECT record_json FROM records ORDER BY global_id")
        for (record_json,) in cursor:
            record = json.loads(record_json)
            if isinstance(record, dict):
                yield record
