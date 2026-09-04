"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : tests.test_base
  Identifier  : 7ece41bf-f11a-4523-8c06-1762387e9654
  Created     : 2026-09-05
  Purpose     : Prove we retry what is worth retrying and surrender on the rest.
================================================================================
"""

from __future__ import annotations

import pytest
import requests

from digital_gold.api import base
from digital_gold.api.base import ApiError, fetch_json

URL = "https://example.test/data"


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the retry tests instant -- the sleep itself is not under test."""
    monkeypatch.setattr(base.time, "sleep", lambda _seconds: None)


def test_successful_response_is_returned(requests_mock) -> None:
    requests_mock.get(URL, json={"ok": True})

    assert fetch_json(URL, source="Test") == {"ok": True}


def test_rate_limit_is_retried_then_succeeds(requests_mock) -> None:
    requests_mock.get(URL, [
        {"status_code": 429},
        {"status_code": 503},
        {"json": {"ok": True}},
    ])

    assert fetch_json(URL, source="Test") == {"ok": True}
    assert requests_mock.call_count == 3


def test_retries_are_bounded(requests_mock) -> None:
    """A permanently rate-limited upstream must fail, not loop forever."""
    requests_mock.get(URL, status_code=429)

    with pytest.raises(ApiError) as excinfo:
        fetch_json(URL, source="Test")

    assert requests_mock.call_count == base.MAX_ATTEMPTS
    assert excinfo.value.retryable
    assert excinfo.value.status_code == 429


def test_client_error_fails_immediately_without_retrying(requests_mock) -> None:
    """A malformed request will fail identically on every attempt."""
    requests_mock.get(URL, status_code=400, text="bad symbol")

    with pytest.raises(ApiError) as excinfo:
        fetch_json(URL, source="Test")

    assert requests_mock.call_count == 1
    assert not excinfo.value.retryable
    assert "bad symbol" in excinfo.value.message


def test_timeout_is_retried_and_then_reported(requests_mock) -> None:
    requests_mock.get(URL, exc=requests.Timeout)

    with pytest.raises(ApiError, match="timed out"):
        fetch_json(URL, source="Test")

    assert requests_mock.call_count == base.MAX_ATTEMPTS


def test_connection_error_is_retried_and_then_reported(requests_mock) -> None:
    requests_mock.get(URL, exc=requests.ConnectionError("no route"))

    with pytest.raises(ApiError, match="Network error"):
        fetch_json(URL, source="Test")

    assert requests_mock.call_count == base.MAX_ATTEMPTS


def test_non_json_body_is_reported_not_swallowed(requests_mock) -> None:
    requests_mock.get(URL, text="<html>maintenance</html>")

    with pytest.raises(ApiError, match="not valid JSON"):
        fetch_json(URL, source="Test")


def test_error_message_names_the_upstream_and_status() -> None:
    rendered = str(ApiError("Binance", "Upstream is unavailable.", 503, True))

    assert "Binance" in rendered
    assert "503" in rendered


def test_params_are_forwarded(requests_mock) -> None:
    requests_mock.get(URL, json=[])

    fetch_json(URL, source="Test", params={"symbol": "BTCUSDT", "limit": 5})

    assert requests_mock.last_request.qs["symbol"] == ["btcusdt"]
