"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : tests.test_frankfurter
  Identifier  : 946115ab-3dbf-4cc0-a4b2-db1aae0ad9ff
  Created     : 2026-09-05
  Purpose     : Lock the FX inversion -- a sign error here flips every finding.
================================================================================
"""

from __future__ import annotations

import pytest

from digital_gold.api.base import ApiError
from digital_gold.api.frankfurter import fetch_fx_rates

_URL = "https://api.frankfurter.dev/v1/2024-01-01..2024-01-03"

_PAYLOAD = {
    "amount": 1.0,
    "base": "USD",
    "rates": {
        "2024-01-02": {"CHF": 0.84, "JPY": 140.0},
        "2024-01-03": {"CHF": 0.80, "JPY": 145.0},
    },
}


def test_rates_are_inverted_to_usd_per_unit(requests_mock) -> None:
    """Upstream gives CHF-per-USD; we must publish USD-per-CHF."""
    requests_mock.get(_URL, json=_PAYLOAD)

    frame = fetch_fx_rates(["CHF", "JPY"], "2024-01-01", "2024-01-03")

    assert frame.loc["2024-01-02", "CHF"] == pytest.approx(1 / 0.84)
    assert frame.loc["2024-01-03", "JPY"] == pytest.approx(1 / 145.0)


def test_strengthening_currency_produces_a_rising_line(requests_mock) -> None:
    """CHF going 0.84 -> 0.80 per USD means CHF strengthened, so our series
    must RISE. If this ever inverts, every correlation sign flips silently."""
    requests_mock.get(_URL, json=_PAYLOAD)

    chf = fetch_fx_rates(["CHF"], "2024-01-01", "2024-01-03")["CHF"]

    assert chf.iloc[1] > chf.iloc[0]


def test_missing_currency_is_reported_not_ignored(requests_mock) -> None:
    requests_mock.get(_URL, json={"rates": {"2024-01-02": {"CHF": 0.84}}})

    with pytest.raises(ApiError, match="JPY"):
        fetch_fx_rates(["CHF", "JPY"], "2024-01-01", "2024-01-03")


def test_empty_response_raises(requests_mock) -> None:
    requests_mock.get(_URL, json={"rates": {}})

    with pytest.raises(ApiError):
        fetch_fx_rates(["CHF"], "2024-01-01", "2024-01-03")


def test_no_currencies_requested_raises() -> None:
    with pytest.raises(ApiError):
        fetch_fx_rates([], "2024-01-01", "2024-01-03")
