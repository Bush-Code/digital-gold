"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : digital_gold.api.binance
  Identifier  : 4abc246e-3153-417c-a985-939c2dd54b62
  Created     : 2026-09-05
  Purpose     : Daily OHLCV history from Binance's public REST API (no key).
================================================================================
"""

from __future__ import annotations

from typing import Any, Final

import pandas as pd

from digital_gold.api.base import ApiError, fetch_json

_BASE_URL: Final[str] = "https://api.binance.com/api/v3/klines"
_SOURCE: Final[str] = "Binance"

# Hard ceiling imposed by the venue. Asking for more is silently truncated to
# 1000, so long histories MUST be paged or the tail is lost without any error.
_MAX_CANDLES_PER_REQUEST: Final[int] = 1000
_MAX_PAGES: Final[int] = 20
_DAY_MS: Final[int] = 86_400_000

_COLUMNS: Final[tuple[str, ...]] = (
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_base", "taker_quote", "ignore",
)


def _to_millis(day: str) -> int:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


def fetch_daily_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Return one row per UTC day for `symbol` between `start` and `end`.

    Pages through the venue's 1000-candle ceiling until the window is covered.

    Returns:
        DataFrame indexed by tz-naive UTC date with float OHLCV columns.
        Empty (correctly typed) if the symbol has no history in the window.

    Raises:
        ApiError: if the venue is unreachable or returns an unexpected shape.
    """
    cursor = _to_millis(start)
    end_ms = _to_millis(end)
    rows: list[list[Any]] = []

    for _ in range(_MAX_PAGES):
        if cursor > end_ms:
            break

        payload = fetch_json(
            _BASE_URL,
            source=_SOURCE,
            params={
                "symbol": symbol,
                "interval": "1d",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": _MAX_CANDLES_PER_REQUEST,
            },
        )

        if not isinstance(payload, list):
            raise ApiError(_SOURCE, f"Expected a list of candles for {symbol}.")
        if not payload:
            break

        rows.extend(payload)

        # Binance's window is inclusive on both ends, so step past the last
        # candle we already hold or the next page repeats it forever.
        cursor = int(payload[-1][0]) + _DAY_MS

        if len(payload) < _MAX_CANDLES_PER_REQUEST:
            break

    return _to_frame(rows)


def _to_frame(rows: list[list[Any]]) -> pd.DataFrame:
    numeric = ["open", "high", "low", "close", "volume"]

    if not rows:
        empty = pd.DataFrame(columns=numeric).astype("float64")
        empty.index = pd.DatetimeIndex([], name="date")
        return empty

    frame = pd.DataFrame(rows, columns=list(_COLUMNS))
    frame["date"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True).dt.tz_localize(None)
    frame = frame.set_index("date").sort_index()
    frame = frame[~frame.index.duplicated(keep="first")]

    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame[numeric].astype("float64")


def fetch_close_series(symbol: str, start: str, end: str) -> pd.Series:
    """Closing prices only -- the single column the analysis layer consumes."""
    return fetch_daily_ohlcv(symbol, start, end)["close"].rename(symbol)
