"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : digital_gold.api.frankfurter
  Identifier  : c40ab871-67bd-489a-aec9-119181972722
  Created     : 2026-09-05
  Purpose     : ECB daily reference FX rates via Frankfurter (no key).
================================================================================
"""

from __future__ import annotations

from typing import Final

import pandas as pd

from digital_gold.api.base import ApiError, fetch_json

_BASE_URL: Final[str] = "https://api.frankfurter.dev/v1"
_SOURCE: Final[str] = "Frankfurter (ECB)"


def fetch_fx_rates(currencies: list[str], start: str, end: str) -> pd.DataFrame:
    """Return the USD value of one unit of each currency, per ECB business day.

    The upstream quotes USD as the base -- "how many CHF per 1 USD" -- which
    moves *inversely* to the currency's strength. We invert to "USD per 1 CHF"
    so that on every chart in this project, a rising line means a strengthening
    asset. Mixing the two conventions would silently flip the sign of every
    correlation against Bitcoin.

    Raises:
        ApiError: if the upstream is unreachable or omits a requested currency.
    """
    if not currencies:
        raise ApiError(_SOURCE, "No currencies requested.")

    payload = fetch_json(
        f"{_BASE_URL}/{start}..{end}",
        source=_SOURCE,
        params={"base": "USD", "symbols": ",".join(sorted(currencies))},
    )

    rates = payload.get("rates") if isinstance(payload, dict) else None
    if not rates:
        raise ApiError(_SOURCE, f"No FX rates returned for {start}..{end}.")

    frame = pd.DataFrame.from_dict(rates, orient="index")
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    frame.index.name = "date"

    missing = sorted(set(currencies) - set(frame.columns))
    if missing:
        raise ApiError(_SOURCE, f"Upstream omitted: {', '.join(missing)}.")

    inverted = 1.0 / frame[sorted(currencies)].astype("float64")
    return inverted.replace([float("inf"), float("-inf")], pd.NA).dropna(how="all")
