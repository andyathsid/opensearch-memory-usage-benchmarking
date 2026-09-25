from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any, Iterable


def coverage_values(record: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    authors: set[str] = set()
    subjects: set[str] = set()
    affiliations: set[str] = set()

    metadata_blocks = record.get("metadataBlocks")
    if isinstance(metadata_blocks, dict):
        citation = metadata_blocks.get("citation")
        if isinstance(citation, dict):
            fields = citation.get("fields", [])
            if isinstance(fields, list):
                for field in fields:
                    if not isinstance(field, dict):
                        continue
                    field_type = field.get("typeName")
                    value = field.get("value")
                    if field_type == "author" and isinstance(value, list):
                        for author in value:
                            if not isinstance(author, dict):
                                continue
                            name = _compound_value(author, "authorName")
                            affiliation = _compound_value(author, "authorAffiliation")
                            if name:
                                authors.add(name)
                            if affiliation:
                                affiliations.add(affiliation)
                    elif field_type == "subject" and isinstance(value, list):
                        subjects.update(
                            subject
                            for raw_subject in value
                            if (subject := _nonempty_string(raw_subject)) is not None
                        )

    top_level_authors = record.get("authors")
    if isinstance(top_level_authors, list):
        authors.update(
            author
            for raw_author in top_level_authors
            if (author := _nonempty_string(raw_author)) is not None
        )

    top_level_subjects = record.get("subjects")
    if isinstance(top_level_subjects, list):
        subjects.update(
            subject
            for raw_subject in top_level_subjects
            if (subject := _nonempty_string(raw_subject)) is not None
        )

    return authors, subjects, affiliations


def build_coverage_report(
    records: Iterable[dict[str, Any]], catalog_complete: bool
) -> dict[str, Any]:
    author_counts: Counter[str] = Counter()
    subject_counts: Counter[str] = Counter()
    affiliation_counts: Counter[str] = Counter()
    dataset_records = 0

    for record in records:
        dataset_records += 1
        authors, subjects, affiliations = coverage_values(record)
        author_counts.update(authors)
        subject_counts.update(subjects)
        affiliation_counts.update(affiliations)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_records": dataset_records,
        "catalog_complete": catalog_complete,
        "unique_counts": {
            "authors": len(author_counts),
            "subjects": len(subject_counts),
            "author_affiliations": len(affiliation_counts),
        },
        "authors": _counter_entries(author_counts),
        "subjects": _counter_entries(subject_counts),
        "author_affiliations": _counter_entries(affiliation_counts),
    }


def _nonempty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _compound_value(compound: dict[str, Any], field_name: str) -> str | None:
    field = compound.get(field_name)
    if not isinstance(field, dict):
        return None
    return _nonempty_string(field.get("value"))


def _counter_entries(counts: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"value": value, "dataset_count": counts[value]}
        for value in sorted(counts, key=str.casefold)
    ]
