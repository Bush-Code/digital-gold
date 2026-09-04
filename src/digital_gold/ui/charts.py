"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : digital_gold.ui.charts
  Identifier  : 1b07fdc9-eb2e-404d-848d-ae4ad629dbe9
  Created     : 2026-09-05
  Purpose     : Every figure the app draws, on one validated colour system.
================================================================================
"""

from __future__ import annotations

from typing import Final

import pandas as pd
import plotly.graph_objects as go

# Palette steps validated for this dark surface with the project's colour
# validator: 8 slots pass the adjacent pairlist (lines), and the first 3 pass
# the stricter all-pairs test used by scatter plots. Do not extend by eye --
# no fourth hue clears all-pairs, which is why the scatter groups into three.
SURFACE: Final[str] = "#1a1a19"
TEXT_PRIMARY: Final[str] = "#ffffff"
TEXT_SECONDARY: Final[str] = "#c3c2b7"
GRID: Final[str] = "#383835"

SERIES: Final[tuple[str, ...]] = (
    "#3987e5", "#d95926", "#199e70", "#c98500",
    "#d55181", "#008300", "#9085e9", "#e66767",
)
MAX_SERIES: Final[int] = len(SERIES)

# Diverging: two opposite poles with a neutral grey midpoint at zero, so "no
# relationship" reads as absence of colour rather than as a third hue.
DIVERGING: Final[list[list]] = [
    [0.0, "#3987e5"], [0.25, "#7fb0ee"], [0.5, GRID],
    [0.75, "#ef9d9d"], [1.0, "#e66767"],
]

_FONT = dict(family="system-ui, -apple-system, sans-serif", size=13)


def _base_layout(title: str, y_title: str, x_title: str = "") -> dict:
    # The title sits at the very top of the paper and the legend just under it,
    # both inside a top margin deep enough for the legend to wrap onto a second
    # row. Narrow side-by-side columns wrap a four-item legend, and a shallower
    # margin drops that second row straight through the title.
    return dict(
        title=dict(text=title, font=dict(size=17, color=TEXT_PRIMARY),
                   x=0, xanchor="left", y=0.98, yanchor="top"),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=TEXT_SECONDARY, **_FONT),
        xaxis=dict(
            title=x_title, gridcolor=GRID, zeroline=False,
            linecolor=GRID, showspikes=True, spikecolor=TEXT_SECONDARY,
            spikethickness=1, spikemode="across", spikedash="dot",
        ),
        yaxis=dict(title=y_title, gridcolor=GRID, zeroline=False, linecolor=GRID),
        hovermode="x unified",
        margin=dict(l=60, r=30, t=104, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
    )


def performance_chart(rebased: pd.DataFrame, labels: dict[str, str]) -> go.Figure:
    """Growth of an equal starting stake, every series indexed to 100.

    Indexing to a common base is what lets a $90,000 asset and a $1.10 currency
    share one axis honestly -- the alternative, two y-scales, can be made to
    show any relationship you like and is never used in this project.
    """
    figure = go.Figure()

    for slot, column in enumerate(rebased.columns[:MAX_SERIES]):
        figure.add_trace(
            go.Scatter(
                x=rebased.index,
                y=rebased[column],
                name=labels.get(column, column),
                mode="lines",
                line=dict(color=SERIES[slot], width=2),
                hovertemplate="%{y:.1f}<extra>" + labels.get(column, column) + "</extra>",
            )
        )

    figure.update_layout(**_base_layout("Growth of 100 units invested", "Index (start = 100)"))
    return figure


def correlation_heatmap(matrix: pd.DataFrame, labels: dict[str, str]) -> go.Figure:
    """Pairwise correlation on a diverging scale anchored at zero."""
    names = [labels.get(c, c) for c in matrix.columns]

    figure = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=names,
            y=names,
            colorscale=DIVERGING,
            zmid=0.0,
            zmin=-1.0,
            zmax=1.0,
            text=matrix.round(2).values,
            texttemplate="%{text}",
            textfont=dict(size=11, color=TEXT_PRIMARY),
            hovertemplate="%{y} vs %{x}<br>r = %{z:.2f}<extra></extra>",
            colorbar=dict(title="r", tickfont=dict(color=TEXT_SECONDARY)),
            xgap=2,
            ygap=2,
        )
    )

    layout = _base_layout("Daily-return correlation", "")
    layout["hovermode"] = "closest"
    layout["xaxis"].update(showspikes=False, gridcolor=SURFACE)
    layout["yaxis"].update(gridcolor=SURFACE, autorange="reversed")
    figure.update_layout(**layout)
    return figure


def rolling_correlation_chart(
    rolled: pd.DataFrame, target_label: str, labels: dict[str, str], window: int
) -> go.Figure:
    """Correlation through time -- the view that exposes regime change."""
    figure = go.Figure()

    for slot, column in enumerate(rolled.columns[:MAX_SERIES]):
        figure.add_trace(
            go.Scatter(
                x=rolled.index,
                y=rolled[column],
                name=labels.get(column, column),
                mode="lines",
                line=dict(color=SERIES[slot], width=2),
                hovertemplate="r = %{y:.2f}<extra>" + labels.get(column, column) + "</extra>",
            )
        )

    figure.add_hline(y=0, line=dict(color=TEXT_SECONDARY, width=1, dash="dash"))
    figure.update_layout(
        **_base_layout(f"{window}-day rolling correlation vs {target_label}", "Correlation (r)")
    )
    figure.update_yaxes(range=[-1, 1])
    return figure


def risk_return_scatter(summary: pd.DataFrame, groups: dict[str, str],
                        labels: dict[str, str]) -> go.Figure:
    """Return against volatility, grouped into the three families under test.

    Three groups, not nine: the all-pairs colour test admits exactly three
    hues, and three is also the comparison the question needs -- crypto,
    real gold, and currencies. Every point is directly labelled, so identity
    never rests on colour alone.
    """
    figure = go.Figure()
    order = ["Crypto", "Gold", "Currency"]

    for slot, group in enumerate(order):
        members = [c for c in summary.index if groups.get(c) == group]
        if not members:
            continue
        subset = summary.loc[members]
        figure.add_trace(
            go.Scatter(
                x=subset["Annualised Volatility"],
                y=subset["Annualised Return"],
                name=group,
                mode="markers+text",
                marker=dict(size=14, color=SERIES[slot],
                            line=dict(color=SURFACE, width=2)),
                text=[labels.get(m, m) for m in members],
                textposition="top center",
                textfont=dict(color=TEXT_SECONDARY, size=11),
                hovertemplate=("%{text}<br>Volatility %{x:.1%}"
                               "<br>Return %{y:.1%}<extra></extra>"),
            )
        )

    layout = _base_layout("Risk against reward", "Annualised return", "Annualised volatility")
    layout["hovermode"] = "closest"
    layout["xaxis"].update(tickformat=".0%", showspikes=False)
    layout["yaxis"].update(tickformat=".0%")
    figure.update_layout(**layout)
    figure.add_hline(y=0, line=dict(color=TEXT_SECONDARY, width=1, dash="dash"))
    return figure


def stress_comparison_chart(asset_label: str, asset_stress: float,
                            gold_stress: float) -> go.Figure:
    """The headline test: the asset beside real gold, on the same bad days."""
    names = [asset_label, "Gold (PAXG)"]
    values = [asset_stress, gold_stress]

    figure = go.Figure(
        go.Bar(
            x=names,
            y=values,
            marker=dict(color=[SERIES[0], SERIES[1]],
                        line=dict(color=SURFACE, width=2)),
            text=[f"{v:+.2f}" for v in values],
            textposition="outside",
            textfont=dict(color=TEXT_PRIMARY, size=14),
            hovertemplate="%{x}<br>r = %{y:.2f}<extra></extra>",
            width=0.5,
        )
    )

    layout = _base_layout(
        "Correlation with falling markets, on the worst days only",
        "Correlation (r)",
    )
    layout["hovermode"] = "closest"
    layout["xaxis"].update(showspikes=False, gridcolor=SURFACE)
    layout["showlegend"] = False
    figure.update_layout(**layout)
    figure.add_hline(y=0, line=dict(color=TEXT_SECONDARY, width=1))
    return figure
