from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .coverage import build_coverage_report
from .harvest import HarvestResult
from .store import MetadataStore


def export_outputs(
    store: MetadataStore,
    output_dir: Path,
    result: HarvestResult,
    requested_target: int | None,
    base_url: str,
    subtree: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets_path = output_dir / "datasets.ndjson"
    coverage_path = output_dir / "coverage.json"
    manifest_path = output_dir / "manifest.json"

    _atomic_write_lines(
        datasets_path,
        (
            json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            for record in store.records()
        ),
    )
    coverage_report = build_coverage_report(store.records(), result.catalog_complete)
    _atomic_write_json(coverage_path, coverage_report)

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "base_url": base_url.rstrip("/"),
            "subtree": subtree,
            "endpoint": "/api/search",
            "record_type": "dataset",
            "metadata_fields": "citation:*",
        },
        "requested_target": "all" if requested_target is None else requested_target,
        "record_count": result.record_count,
        "repository_total_at_last_request": result.repository_total,
        "next_start": result.next_start,
        "catalog_complete": result.catalog_complete,
        "files": {
            "datasets": datasets_path.name,
            "coverage": coverage_path.name,
            "database": store.path.name,
        },
    }
    _atomic_write_json(manifest_path, manifest)


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_lines(
        path,
        [json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"],
    )


def _atomic_write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
