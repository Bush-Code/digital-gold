"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : digital_gold.analysis.metrics
  Identifier  : 760536bc-9533-4db6-bab7-71cbef006d93
  Created     : 2026-09-05
  Purpose     : Descriptive risk/return statistics over an aligned price panel.
================================================================================
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from digital_gold.config import TRADING_DAYS_PER_YEAR


def align_panel(frames: list[pd.Series | pd.DataFrame]) -> pd.DataFrame:
    """Join every series onto the dates that ALL sources actually quote.

    Crypto trades 24/7; ECB reference rates exist only on business days. An
    outer join would leave weekend NaNs in the FX columns, and forward-filling
    them would invent flat weekend "observations" that drag every correlation
    toward zero. We therefore intersect: one row per day on which every
    instrument genuinely traded, and returns measured between those rows.
    """
    usable = [f for f in frames if f is not None and len(f) > 0]
    if not usable:
        return pd.DataFrame()

    panel = pd.concat(usable, axis=1, join="inner")
    panel = panel.sort_index()
    panel = panel[~panel.index.duplicated(keep="first")]
    return panel.dropna(how="any")


def daily_returns(panel: pd.DataFrame) -> pd.DataFrame:
    """Simple period-over-period returns, first (undefined) row dropped."""
    return panel.pct_change().iloc[1:]


def rebase_to_100(panel: pd.DataFrame) -> pd.DataFrame:
    """Index every column to 100 at its first observation for comparability."""
    if panel.empty:
        return panel
    first = panel.iloc[0]
    safe = first.replace(0, np.nan)
    return panel.divide(safe, axis=1) * 100.0


def annualised_volatility(returns: pd.DataFrame) -> pd.Series:
    """Standard deviation of daily returns, scaled to a year."""
    return returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)


def annualised_return(panel: pd.DataFrame) -> pd.Series:
    """Compound annual growth rate implied by the first and last price."""
    if len(panel) < 2:
        return pd.Series(dtype="float64", index=panel.columns)

    years = (panel.index[-1] - panel.index[0]).days / 365.25
    if years <= 0:
        return pd.Series(dtype="float64", index=panel.columns)

    growth = panel.iloc[-1] / panel.iloc[0].replace(0, np.nan)
    return growth.pow(1.0 / years) - 1.0


def max_drawdown(panel: pd.DataFrame) -> pd.Series:
    """Deepest peak-to-trough fall, as a negative fraction.

    This is the number that separates a store of value from a risk asset far
    more honestly than volatility does.
    """
    if panel.empty:
        return pd.Series(dtype="float64", index=panel.columns)
    running_peak = panel.cummax()
    return (panel / running_peak - 1.0).min()


def summary_table(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per instrument with the headline descriptive statistics."""
    if panel.empty:
        return pd.DataFrame()

    returns = daily_returns(panel)
    return pd.DataFrame(
        {
            "Annualised Return": annualised_return(panel),
            "Annualised Volatility": annualised_volatility(returns),
            "Max Drawdown": max_drawdown(panel),
        }
    )
