from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import HarvestError


DEFAULT_BASE_URL = "https://data.brin.go.id"
DEFAULT_SUBTREE = "BRIN_ID"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class SearchPage:
    items: list[dict[str, Any]]
    total_count: int
    start: int


class DataverseClient:
    """Small client for the public Dataverse Search API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        subtree: str = DEFAULT_SUBTREE,
        timeout_seconds: float = 30.0,
        max_retries: int = 5,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.subtree = subtree
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.sleeper = sleeper

    def search(self, start: int, per_page: int) -> SearchPage:
        parameters = {
            "q": "*",
            "type": "dataset",
            "subtree": self.subtree,
            "start": start,
            "per_page": per_page,
            "show_entity_ids": "true",
            "metadata_fields": "citation:*",
        }
        url = f"{self.base_url}/api/search?{urlencode(parameters)}"
        payload = self._get_json(url)

        if payload.get("status") != "OK" or not isinstance(payload.get("data"), dict):
            raise HarvestError(f"Dataverse returned an unexpected response for {url}")

        data = payload["data"]
        items = data.get("items")
        total_count = data.get("total_count")
        response_start = data.get("start", start)
        if not isinstance(items, list) or not isinstance(total_count, int):
            raise HarvestError(f"Dataverse response is missing items or total_count for {url}")

        return SearchPage(items=items, total_count=total_count, start=int(response_start))

    def _get_json(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "brin-metadata-harvester/1.0 (public research metadata)",
            },
        )

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    result = json.load(response)
                if not isinstance(result, dict):
                    raise HarvestError(f"Dataverse returned non-object JSON for {url}")
                return result
            except HTTPError as error:
                if error.code not in RETRYABLE_STATUS_CODES or attempt == self.max_retries:
                    raise HarvestError(f"HTTP {error.code} while requesting {url}") from error
                delay_seconds = retry_delay_seconds(error.headers.get("Retry-After"), attempt)
            except (TimeoutError, URLError, json.JSONDecodeError) as error:
                if attempt == self.max_retries:
                    raise HarvestError(f"Request failed after retries: {url}: {error}") from error
                delay_seconds = retry_delay_seconds(None, attempt)

            self.sleeper(delay_seconds)

        raise AssertionError("retry loop must return or raise")


def retry_delay_seconds(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return min(30.0, (2**attempt) + random.uniform(0.0, 0.5))
