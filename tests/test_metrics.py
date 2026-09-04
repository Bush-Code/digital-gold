"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : tests.test_metrics
  Identifier  : 5e46b2f8-3b6c-49e4-9b43-8ced90cceebd
  Created     : 2026-09-05
  Purpose     : Verify the 24/7-vs-business-day join and the risk statistics.
================================================================================
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from digital_gold.analysis.metrics import (
    align_panel,
    annualised_return,
    annualised_volatility,
    daily_returns,
    max_drawdown,
    rebase_to_100,
    summary_table,
)


def _crypto_series() -> pd.Series:
    """Seven consecutive days -- crypto never closes."""
    return pd.Series(
        [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        index=pd.date_range("2024-01-01", periods=7, freq="D"),
        name="BTCUSDT",
    )


def _fx_series() -> pd.Series:
    """Business days only -- the ECB does not publish on weekends."""
    return pd.Series(
        [1.10, 1.11, 1.12, 1.13, 1.14],
        index=pd.bdate_range("2024-01-01", periods=5),
        name="CHF",
    )


def test_align_panel_keeps_only_days_both_sources_quote() -> None:
    """The weekend must be dropped, never forward-filled into fake flat days."""
    panel = align_panel([_crypto_series(), _fx_series()])

    assert len(panel) == 5
    assert list(panel.columns) == ["BTCUSDT", "CHF"]
    assert not panel.isna().any().any()
    weekdays = {ts.weekday() for ts in panel.index}
    assert weekdays.isdisjoint({5, 6}), "no Saturday or Sunday rows"


def test_align_panel_handles_no_usable_input() -> None:
    assert align_panel([]).empty
    assert align_panel([pd.Series(dtype="float64")]).empty


def test_daily_returns_drops_the_undefined_first_row() -> None:
    panel = pd.DataFrame({"A": [100.0, 110.0, 121.0]})

    returns = daily_returns(panel)

    assert len(returns) == 2
    assert returns["A"].iloc[0] == pytest.approx(0.10)


def test_rebase_starts_every_series_at_100() -> None:
    panel = pd.DataFrame({"A": [50.0, 75.0], "B": [200.0, 100.0]})

    rebased = rebase_to_100(panel)

    assert rebased.iloc[0].tolist() == [100.0, 100.0]
    assert rebased["A"].iloc[1] == pytest.approx(150.0)
    assert rebased["B"].iloc[1] == pytest.approx(50.0)


def test_max_drawdown_measures_peak_to_trough() -> None:
    panel = pd.DataFrame({"A": [100.0, 200.0, 50.0, 80.0]})

    assert max_drawdown(panel)["A"] == pytest.approx(-0.75)


def test_max_drawdown_is_zero_for_a_series_that_only_rises() -> None:
    panel = pd.DataFrame({"A": [10.0, 20.0, 30.0]})

    assert max_drawdown(panel)["A"] == pytest.approx(0.0)


def test_annualised_return_recovers_a_known_doubling() -> None:
    """Exactly one year, exactly 2x, must give ~100%."""
    panel = pd.DataFrame(
        {"A": [100.0, 200.0]},
        index=pd.to_datetime(["2024-01-01", "2025-01-01"]),
    )

    assert annualised_return(panel)["A"] == pytest.approx(1.0, abs=0.01)


def test_annualised_volatility_scales_by_root_252() -> None:
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.01, -0.01, 0.01]})

    expected = returns["A"].std(ddof=1) * np.sqrt(252)

    assert annualised_volatility(returns)["A"] == pytest.approx(expected)


def test_summary_table_reports_every_instrument() -> None:
    panel = pd.DataFrame(
        {"BTCUSDT": [100.0, 120.0, 90.0], "PAXGUSDT": [50.0, 51.0, 52.0]},
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
    )

    table = summary_table(panel)

    assert set(table.index) == {"BTCUSDT", "PAXGUSDT"}
    assert "Max Drawdown" in table.columns
    assert table.loc["PAXGUSDT", "Max Drawdown"] == pytest.approx(0.0)


def test_summary_table_on_empty_panel_is_empty() -> None:
    assert summary_table(pd.DataFrame()).empty
