from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .client import DEFAULT_BASE_URL, DEFAULT_SUBTREE, DataverseClient
from .errors import HarvestError
from .harvest import HarvestResult, harvest
from .reporting import export_outputs
from .store import MetadataStore


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "brin"
DEFAULT_TARGET = 1_000


def parse_target(value: str) -> int | None:
    if value.casefold() == "all":
        return None
    try:
        target = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("target must be a positive integer or 'all'") from error
    if target < 1:
        raise argparse.ArgumentTypeError("target must be a positive integer or 'all'")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Harvest public BRIN dataset metadata into resumable SQLite and NDJSON files."
    )
    parser.add_argument(
        "--target",
        type=parse_target,
        default=DEFAULT_TARGET,
        help="Total dataset records desired, or 'all' (default: 1000).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--subtree", default=DEFAULT_SUBTREE)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between API pages.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds.")
    parser.add_argument("--max-retries", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    _validate_arguments(parser, arguments)

    output_dir: Path = arguments.output_dir.resolve()
    database_path = output_dir / "brin_metadata.sqlite3"
    client = DataverseClient(
        base_url=arguments.base_url,
        subtree=arguments.subtree,
        timeout_seconds=arguments.timeout,
        max_retries=arguments.max_retries,
    )

    try:
        with MetadataStore(database_path) as store:
            store.ensure_source(arguments.base_url, arguments.subtree)
            try:
                result = harvest(
                    store=store,
                    client=client,
                    target=arguments.target,
                    page_size=arguments.page_size,
                    delay_seconds=arguments.delay,
                )
            except KeyboardInterrupt:
                print("Harvest interrupted; exporting collected records.", file=sys.stderr)
                result = _result_from_store(store)
                export_outputs(
                    store,
                    output_dir,
                    result,
                    arguments.target,
                    arguments.base_url,
                    arguments.subtree,
                )
                return 130

            export_outputs(
                store,
                output_dir,
                result,
                arguments.target,
                arguments.base_url,
                arguments.subtree,
            )
    except HarvestError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    target_description = "all available" if arguments.target is None else str(arguments.target)
    print(f"Finished with {result.record_count} of {target_description} requested records.")
    print(f"Outputs: {output_dir}")
    if result.repository_total is not None and result.record_count < (arguments.target or 0):
        print(f"The API currently exposes {result.repository_total} public dataset records.")
    return 0


def _validate_arguments(parser: argparse.ArgumentParser, arguments: argparse.Namespace) -> None:
    if not 1 <= arguments.page_size <= 1_000:
        parser.error("--page-size must be between 1 and 1000")
    if arguments.delay < 0:
        parser.error("--delay cannot be negative")
    if arguments.timeout <= 0:
        parser.error("--timeout must be positive")
    if arguments.max_retries < 0:
        parser.error("--max-retries cannot be negative")


def _result_from_store(store: MetadataStore) -> HarvestResult:
    repository_total_value = store.get_state("repository_total")
    return HarvestResult(
        record_count=store.count(),
        repository_total=(
            int(repository_total_value) if repository_total_value is not None else None
        ),
        next_start=store.get_int_state("next_start"),
        catalog_complete=store.get_bool_state("catalog_complete"),
    )
