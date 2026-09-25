from __future__ import annotations

import json
from collections.abc import Collection, Iterable, Mapping
from typing import Any, TypedDict

import requests


class RawDocumentsSize(TypedDict):
    document_count: int
    total_size_in_bytes: int
    average_size_in_bytes: float


def get_opensearch_index_size_bytes(
    base_url: str,
    index_name: str,
    username: str | None = None,
    password: str | None = None,
    verify_ssl: bool = True,
    timeout: int = 30,
) -> int:
    """Return primary-shard storage size for an OpenSearch index in bytes."""
    url = f"{base_url.rstrip('/')}/{index_name}/_stats/store"
    auth = (
        (username, password)
        if username is not None and password is not None
        else None
    )

    response = requests.get(
        url,
        auth=auth,
        verify=verify_ssl,
        timeout=timeout,
    )
    response.raise_for_status()

    data = response.json()
    return data["_all"]["primaries"]["store"]["size_in_bytes"]


def calculate_raw_documents_size(
    records: Iterable[Mapping[str, Any]],
    excluded_fields: Collection[str] = ("description_embedding",),
) -> RawDocumentsSize:
    """Calculate compact UTF-8 JSON size without the excluded fields."""
    excluded = frozenset(excluded_fields)
    document_count = 0
    total_size_in_bytes = 0

    for record in records:
        raw_record = {
            field: value
            for field, value in record.items()
            if field not in excluded
        }
        serialized = json.dumps(
            raw_record,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        total_size_in_bytes += len(serialized.encode("utf-8"))
        document_count += 1

    average_size_in_bytes = (
        total_size_in_bytes / document_count if document_count else 0.0
    )
    return {
        "document_count": document_count,
        "total_size_in_bytes": total_size_in_bytes,
        "average_size_in_bytes": average_size_in_bytes,
    }
