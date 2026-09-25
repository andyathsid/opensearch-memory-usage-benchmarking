from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Protocol

from .client import SearchPage
from .errors import HarvestError
from .store import MetadataStore


@dataclass(frozen=True)
class HarvestResult:
    record_count: int
    repository_total: int | None
    next_start: int
    catalog_complete: bool


class SearchClient(Protocol):
    def search(self, start: int, per_page: int) -> SearchPage: ...


def harvest(
    store: MetadataStore,
    client: SearchClient,
    target: int | None,
    page_size: int,
    delay_seconds: float,
    sleeper: Callable[[float], None] = time.sleep,
) -> HarvestResult:
    current_count = store.count()
    next_start = store.get_int_state("next_start")
    repository_total_value = store.get_state("repository_total")
    repository_total = None if repository_total_value is None else int(repository_total_value)
    catalog_complete = store.get_bool_state("catalog_complete")

    while not catalog_complete and (target is None or current_count < target):
        remaining = page_size if target is None else min(page_size, target - current_count)
        page = client.search(start=next_start, per_page=remaining)
        if page.start != next_start:
            raise HarvestError(
                f"Dataverse returned start={page.start}, expected start={next_start}"
            )

        next_start += len(page.items)
        repository_total = page.total_count
        catalog_complete = not page.items or next_start >= repository_total
        store.save_page(page.items, next_start, repository_total, catalog_complete)
        current_count = store.count()

        print(
            f"Collected {current_count} dataset records "
            f"(API position {next_start}/{repository_total})",
            flush=True,
        )
        if not catalog_complete and (target is None or current_count < target):
            sleeper(delay_seconds)

    return HarvestResult(
        record_count=current_count,
        repository_total=repository_total,
        next_start=next_start,
        catalog_complete=catalog_complete,
    )
