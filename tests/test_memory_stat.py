import json
from unittest.mock import Mock, patch

from index_memory_usage import (
    calculate_raw_documents_size,
    get_opensearch_index_size_bytes,
)


@patch("index_memory_usage.memory_stat.requests.get")
def test_get_opensearch_index_size_bytes_returns_primary_store_size(
    get: Mock,
) -> None:
    response = Mock()
    response.json.return_value = {
        "_all": {
            "primaries": {
                "store": {"size_in_bytes": 1_000},
            }
        }
    }
    get.return_value = response

    size = get_opensearch_index_size_bytes(
        "https://localhost:9200/",
        "datasets",
        username="admin",
        password="secret",
        verify_ssl=False,
        timeout=10,
    )

    get.assert_called_once_with(
        "https://localhost:9200/datasets/_stats/store",
        auth=("admin", "secret"),
        verify=False,
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()
    assert size == 1_000


def test_calculate_raw_documents_size_excludes_embedding() -> None:
    records = [
        {
            "name": "Kopi",
            "description": "Penelitian kopi",
            "description_embedding": [0.1, 0.2],
        },
        {
            "name": "Mangga",
            "description": "Penelitian mangga",
            "description_embedding": [0.3, 0.4],
        },
    ]
    expected_documents = [
        {"name": "Kopi", "description": "Penelitian kopi"},
        {"name": "Mangga", "description": "Penelitian mangga"},
    ]
    expected_size = sum(
        len(
            json.dumps(
                document,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        for document in expected_documents
    )

    size = calculate_raw_documents_size(records)

    assert size == {
        "document_count": 2,
        "total_size_in_bytes": expected_size,
        "average_size_in_bytes": expected_size / 2,
    }


def test_calculate_raw_documents_size_accepts_empty_iterable() -> None:
    assert calculate_raw_documents_size([]) == {
        "document_count": 0,
        "total_size_in_bytes": 0,
        "average_size_in_bytes": 0.0,
    }
