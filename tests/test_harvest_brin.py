from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.scraping.brin.cli import parse_target
from scripts.scraping.brin.client import SearchPage
from scripts.scraping.brin.coverage import build_coverage_report, coverage_values
from scripts.scraping.brin.harvest import HarvestResult, harvest
from scripts.scraping.brin.reporting import export_outputs
from scripts.scraping.brin.store import MetadataStore


def dataset(global_id: str, author: str, subject: str, affiliation: str) -> dict:
    return {
        "global_id": global_id,
        "type": "dataset",
        "authors": [author],
        "subjects": [subject],
        "metadataBlocks": {
            "citation": {
                "fields": [
                    {
                        "typeName": "author",
                        "value": [
                            {
                                "authorName": {"value": author},
                                "authorAffiliation": {"value": affiliation},
                            }
                        ],
                    },
                    {"typeName": "subject", "value": [subject]},
                ]
            }
        },
    }


class FakeClient:
    def __init__(self, records: list[dict]) -> None:
        self.records = records
        self.calls: list[tuple[int, int]] = []

    def search(self, start: int, per_page: int) -> SearchPage:
        self.calls.append((start, per_page))
        return SearchPage(
            items=self.records[start : start + per_page],
            total_count=len(self.records),
            start=start,
        )


class HarvestBrinTests(unittest.TestCase):
    def test_harvest_resumes_from_saved_position_without_duplicates(self) -> None:
        records = [
            dataset(f"hdl:test/{index}", f"Author {index}", "Other", f"Org {index}")
            for index in range(5)
        ]
        client = FakeClient(records)

        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "metadata.sqlite3"
            with MetadataStore(database_path) as store:
                first = harvest(store, client, target=3, page_size=2, delay_seconds=0)
                second = harvest(store, client, target=5, page_size=2, delay_seconds=0)

                self.assertEqual(3, first.record_count)
                self.assertEqual(5, second.record_count)
                self.assertTrue(second.catalog_complete)
                self.assertEqual(5, store.count())
                self.assertEqual([(0, 2), (2, 1), (3, 2)], client.calls)

    def test_coverage_uses_literal_metadata_values(self) -> None:
        record = dataset("hdl:test/1", "  Jane Doe  ", "Social Sciences", "  BRIN ")

        authors, subjects, affiliations = coverage_values(record)

        self.assertEqual({"Jane Doe"}, authors)
        self.assertEqual({"Social Sciences"}, subjects)
        self.assertEqual({"BRIN"}, affiliations)

        report = build_coverage_report([record, record], catalog_complete=False)
        self.assertEqual(1, report["unique_counts"]["authors"])
        self.assertEqual(2, report["authors"][0]["dataset_count"])
        self.assertFalse(report["catalog_complete"])

    def test_export_writes_ndjson_coverage_and_manifest(self) -> None:
        record = dataset("hdl:test/1", "Jane Doe", "Social Sciences", "BRIN")
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            with MetadataStore(output_dir / "brin_metadata.sqlite3") as store:
                store.save_page([record], 1, 10, False)
                result = HarvestResult(1, 10, 1, False)
                export_outputs(
                    store,
                    output_dir,
                    result,
                    requested_target=1,
                    base_url="https://example.test",
                    subtree="ROOT",
                )

            exported = json.loads((output_dir / "datasets.ndjson").read_text("utf-8"))
            coverage = json.loads((output_dir / "coverage.json").read_text("utf-8"))
            manifest = json.loads((output_dir / "manifest.json").read_text("utf-8"))

            self.assertEqual("hdl:test/1", exported["global_id"])
            self.assertEqual(1, coverage["unique_counts"]["author_affiliations"])
            self.assertEqual(1, manifest["record_count"])
            self.assertFalse(manifest["catalog_complete"])

    def test_parse_target_accepts_integer_and_all(self) -> None:
        self.assertEqual(1_000, parse_target("1000"))
        self.assertIsNone(parse_target("all"))


if __name__ == "__main__":
    unittest.main()
