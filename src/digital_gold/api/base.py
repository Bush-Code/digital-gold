"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : digital_gold.api.base
  Identifier  : 5524ce4b-f4ee-4c73-96d8-018155b5a48d
  Created     : 2026-09-05
  Purpose     : One HTTP path for every upstream call, with structured failures.
================================================================================
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Final

import requests

DEFAULT_TIMEOUT: Final[float] = 20.0
MAX_ATTEMPTS: Final[int] = 3
BACKOFF_SECONDS: Final[float] = 1.5

_RETRYABLE_STATUS: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class ApiError(Exception):
    """A failure we can render to the user instead of a raw traceback.

    Every upstream problem -- timeout, HTTP status, malformed body -- arrives
    as this one type, so callers need exactly one except clause and the UI has
    a guaranteed `message` to display.
    """

    source: str
    message: str
    status_code: int | None = None
    retryable: bool = False

    def __str__(self) -> str:
        where = f"{self.source}"
        if self.status_code is not None:
            where += f" (HTTP {self.status_code})"
        return f"{where}: {self.message}"


def fetch_json(
    url: str,
    source: str,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """GET `url` and decode JSON, retrying only what is worth retrying.

    Raises:
        ApiError: on any failure, with the upstream named and a usable message.
    """
    last_error: ApiError | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except requests.Timeout:
            last_error = ApiError(source, f"Request timed out after {timeout}s.", None, True)
        except requests.RequestException as exc:
            last_error = ApiError(source, f"Network error: {exc}", None, True)
        else:
            if response.status_code in _RETRYABLE_STATUS:
                last_error = ApiError(
                    source,
                    "Upstream is rate-limiting or unavailable.",
                    response.status_code,
                    True,
                )
            elif not response.ok:
                raise ApiError(
                    source,
                    f"Request rejected: {response.text[:200]}",
                    response.status_code,
                    False,
                )
            else:
                try:
                    return response.json()
                except ValueError as exc:
                    raise ApiError(source, f"Response was not valid JSON: {exc}") from exc

        # Only retryable paths fall through to here.
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS * attempt)

    raise last_error or ApiError(source, "Request failed for an unknown reason.")
