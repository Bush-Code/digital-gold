"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : tests.test_charts
  Identifier  : e2da685f-5640-4795-832b-300d47abf3f2
  Created     : 2026-09-05
  Purpose     : Hold the figures to the project's charting rules.
================================================================================
"""

from __future__ import annotations

import pandas as pd
import pytest

from digital_gold.ui import charts

LABELS = {
    "BTCUSDT": "Bitcoin", "ETHUSDT": "Ethereum",
    "PAXGUSDT": "Gold (PAXG)", "CHF": "Swiss Franc",
}


@pytest.fixture
def panel() -> pd.DataFrame:
    index = pd.bdate_range("2024-01-01", periods=40)
    return pd.DataFrame(
        {
            "BTCUSDT": range(100, 140),
            "ETHUSDT": range(50, 90),
            "PAXGUSDT": range(200, 240),
            "CHF": [1.1 + i * 0.001 for i in range(40)],
        },
        index=index,
        dtype="float64",
    )


def test_performance_chart_draws_one_line_per_instrument(panel: pd.DataFrame) -> None:
    figure = charts.performance_chart(panel, LABELS)

    assert len(figure.data) == 4
    assert {trace.name for trace in figure.data} == set(LABELS.values())
    assert all(trace.mode == "lines" for trace in figure.data)


def test_series_are_coloured_in_fixed_slot_order(panel: pd.DataFrame) -> None:
    """Colour follows position, never a cycled or generated hue."""
    figure = charts.performance_chart(panel, LABELS)

    used = [trace.line.color for trace in figure.data]
    assert used == list(charts.SERIES[:4])


def test_performance_chart_never_exceeds_the_validated_slots() -> None:
    wide = pd.DataFrame(
        {f"S{i}": [1.0, 2.0] for i in range(charts.MAX_SERIES + 3)},
        index=pd.bdate_range("2024-01-01", periods=2),
    )

    figure = charts.performance_chart(wide, {})

    assert len(figure.data) == charts.MAX_SERIES


def test_every_figure_uses_a_single_y_axis(panel: pd.DataFrame) -> None:
    """A dual-axis chart can be made to show any relationship; none are allowed."""
    figures = [
        charts.performance_chart(panel, LABELS),
        charts.rolling_correlation_chart(
            panel[["ETHUSDT", "CHF"]], "Bitcoin", LABELS, 20
        ),
        charts.stress_comparison_chart("Bitcoin", 0.03, -0.02),
    ]

    for figure in figures:
        assert not hasattr(figure.layout, "yaxis2") or figure.layout.yaxis2.title.text is None
        assert all(getattr(trace, "yaxis", None) in (None, "y") for trace in figure.data)


def test_correlation_heatmap_is_diverging_and_anchored_at_zero(panel: pd.DataFrame) -> None:
    matrix = panel.pct_change().iloc[1:].corr()

    figure = charts.correlation_heatmap(matrix, LABELS)

    heatmap = figure.data[0]
    assert heatmap.zmid == 0.0
    assert (heatmap.zmin, heatmap.zmax) == (-1.0, 1.0)
    assert heatmap.colorscale[2][1] == charts.GRID, "midpoint must be neutral grey"


def test_rolling_correlation_is_bounded_to_the_valid_range(panel: pd.DataFrame) -> None:
    rolled = panel[["ETHUSDT", "PAXGUSDT"]].pct_change().iloc[1:]

    figure = charts.rolling_correlation_chart(rolled, "Bitcoin", LABELS, 20)

    assert tuple(figure.layout.yaxis.range) == (-1, 1)


def test_scatter_labels_every_point_so_colour_is_never_the_only_cue() -> None:
    summary = pd.DataFrame(
        {
            "Annualised Return": [0.4, 0.14, 0.01],
            "Annualised Volatility": [0.58, 0.18, 0.08],
            "Max Drawdown": [-0.77, -0.28, -0.13],
        },
        index=["BTCUSDT", "PAXGUSDT", "CHF"],
    )
    groups = {"BTCUSDT": "Crypto", "PAXGUSDT": "Gold", "CHF": "Currency"}

    figure = charts.risk_return_scatter(summary, groups, LABELS)

    assert len(figure.data) == 3, "one trace per family"
    for trace in figure.data:
        assert "text" in trace.mode
        assert all(t for t in trace.text)


def test_scatter_stays_within_the_three_all_pairs_validated_hues() -> None:
    summary = pd.DataFrame(
        {"Annualised Return": [0.1] * 3, "Annualised Volatility": [0.2] * 3,
         "Max Drawdown": [-0.1] * 3},
        index=["BTCUSDT", "PAXGUSDT", "CHF"],
    )
    groups = {"BTCUSDT": "Crypto", "PAXGUSDT": "Gold", "CHF": "Currency"}

    figure = charts.risk_return_scatter(summary, groups, LABELS)

    used = [trace.marker.color for trace in figure.data]
    assert used == list(charts.SERIES[:3])


def test_stress_chart_shows_the_asset_beside_gold() -> None:
    figure = charts.stress_comparison_chart("Bitcoin", 0.03, -0.02)

    bar = figure.data[0]
    assert list(bar.x) == ["Bitcoin", "Gold (PAXG)"]
    assert list(bar.y) == [0.03, -0.02]
    assert list(bar.text) == ["+0.03", "-0.02"], "sign must be explicit"


def test_legend_clears_the_title_in_narrow_columns(panel: pd.DataFrame) -> None:
    """Regression: a wrapped legend used to overlap the chart title."""
    figure = charts.performance_chart(panel, LABELS)

    # Legend y is measured against the plot area and title y against the paper,
    # so the two are not numerically comparable. What actually prevents the
    # overlap is a top margin deep enough to seat a wrapped legend beneath a
    # top-pinned title, with the legend growing upward from the plot area.
    assert figure.layout.margin.t >= 100
    assert figure.layout.title.yanchor == "top"
    assert figure.layout.legend.yanchor == "bottom"
    assert figure.layout.legend.y >= 1.0
