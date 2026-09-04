"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : tests.test_binance
  Identifier  : bf970019-bc01-41fd-8435-f3aa6890457d
  Created     : 2026-09-05
  Purpose     : Guard the paging logic that silently truncates long histories.
================================================================================
"""

from __future__ import annotations

import pandas as pd
import pytest

from digital_gold.api.base import ApiError
from digital_gold.api.binance import fetch_close_series, fetch_daily_ohlcv

DAY_MS = 86_400_000
START_MS = 1_502_928_000_000  # 2017-08-17


def _candle(open_time: int, close: float) -> list:
    return [open_time, "1.0", "2.0", "0.5", str(close), "10.0",
            open_time + DAY_MS - 1, "100.0", 5, "1.0", "1.0", "0"]


def _page(count: int, first_time: int, first_close: float = 100.0) -> list:
    return [_candle(first_time + i * DAY_MS, first_close + i) for i in range(count)]


def test_single_page_is_parsed(requests_mock) -> None:
    requests_mock.get("https://api.binance.com/api/v3/klines", json=_page(3, START_MS))

    frame = fetch_daily_ohlcv("BTCUSDT", "2017-08-17", "2017-08-20")

    assert len(frame) == 3
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert frame["close"].dtype == "float64"
    assert isinstance(frame.index, pd.DatetimeIndex)


def test_pages_until_history_is_exhausted(requests_mock) -> None:
    """A full page must trigger another request; a short page must stop it.

    This is the regression that matters: without paging, an 8-year request
    returns only the most recent 1000 days with no error raised at all.
    """
    full_page = _page(1000, START_MS)
    short_page = _page(4, START_MS + 1000 * DAY_MS, first_close=2000.0)

    requests_mock.get(
        "https://api.binance.com/api/v3/klines",
        [{"json": full_page}, {"json": short_page}, {"json": []}],
    )

    frame = fetch_daily_ohlcv("BTCUSDT", "2017-08-17", "2026-09-05")

    assert len(frame) == 1004, "both pages must be retained"
    assert requests_mock.call_count == 2, "a short page must end the loop"
    assert frame.index.is_monotonic_increasing


def test_page_boundary_candle_is_not_duplicated(requests_mock) -> None:
    """The cursor must step past the last candle held, not re-request it."""
    first = _page(1000, START_MS)
    overlapping = _page(3, START_MS + 999 * DAY_MS)

    requests_mock.get(
        "https://api.binance.com/api/v3/klines",
        [{"json": first}, {"json": overlapping}],
    )

    frame = fetch_daily_ohlcv("BTCUSDT", "2017-08-17", "2026-09-05")

    assert not frame.index.has_duplicates


def test_empty_history_yields_typed_empty_frame(requests_mock) -> None:
    requests_mock.get("https://api.binance.com/api/v3/klines", json=[])

    frame = fetch_daily_ohlcv("NOPEUSDT", "2017-08-17", "2017-08-20")

    assert frame.empty
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]


def test_unexpected_shape_raises_api_error(requests_mock) -> None:
    requests_mock.get("https://api.binance.com/api/v3/klines", json={"code": -1121})

    with pytest.raises(ApiError) as excinfo:
        fetch_daily_ohlcv("BADSYMBOL", "2017-08-17", "2017-08-20")

    assert excinfo.value.source == "Binance"


def test_close_series_is_named_for_its_symbol(requests_mock) -> None:
    requests_mock.get("https://api.binance.com/api/v3/klines", json=_page(2, START_MS))

    series = fetch_close_series("ETHUSDT", "2017-08-17", "2017-08-19")

    assert series.name == "ETHUSDT"
    assert series.iloc[0] == pytest.approx(100.0)
