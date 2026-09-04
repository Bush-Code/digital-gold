"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : main
  Identifier  : b7efbd01-6ef1-4778-8b15-fa8b0153c59b
  Created     : 2026-09-05
  Purpose     : Streamlit entry point. Run with:  streamlit run main.py
================================================================================

Digital Gold? -- an empirical test of whether Bitcoin behaves like gold or like
a risk asset, using two independent public APIs and no API keys.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from digital_gold.analysis.correlation import (  # noqa: E402
    DEFAULT_ROLLING_WINDOW,
    assess_safe_haven,
    correlation_matrix,
    rolling_correlation,
)
from digital_gold.analysis.metrics import (  # noqa: E402
    align_panel,
    daily_returns,
    rebase_to_100,
    summary_table,
)
from digital_gold.api.base import ApiError  # noqa: E402
from digital_gold.api.binance import fetch_close_series  # noqa: E402
from digital_gold.api.frankfurter import fetch_fx_rates  # noqa: E402
from digital_gold.config import (  # noqa: E402
    ALL_INSTRUMENTS,
    BINANCE_INSTRUMENTS,
    BY_CODE,
    EARLIEST_DATE,
    FX_INSTRUMENTS,
    GOLD_CODE,
    AssetClass,
)
from digital_gold.ui import charts  # noqa: E402

CACHE_TTL_SECONDS = 3600
DEFAULT_SELECTION = ("BTCUSDT", "ETHUSDT", "PAXGUSDT", "CHF", "AUD")
RISK_PROXIES = ["AUD", "EUR"]

st.set_page_config(page_title="Digital Gold?", page_icon="🪙", layout="wide")


# --- Data access (cached so widgets never re-hit the APIs) --------------------

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_crypto(symbols: tuple[str, ...], start: str, end: str) -> pd.DataFrame:
    series = [fetch_close_series(s, start, end) for s in symbols]
    return pd.concat(series, axis=1) if series else pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_fx(currencies: tuple[str, ...], start: str, end: str) -> pd.DataFrame:
    return fetch_fx_rates(list(currencies), start, end) if currencies else pd.DataFrame()


def group_of(code: str) -> str:
    """Collapse the four asset classes into the three the scatter can colour."""
    instrument = BY_CODE.get(code)
    if instrument is None:
        return "Currency"
    if instrument.asset_class is AssetClass.CRYPTO:
        return "Crypto"
    if instrument.asset_class is AssetClass.PRECIOUS_METAL:
        return "Gold"
    return "Currency"


# --- Sidebar -----------------------------------------------------------------

st.sidebar.title("🪙 Digital Gold?")
st.sidebar.caption("Binance · Frankfurter (ECB) — no API keys required")

earliest = date.fromisoformat(EARLIEST_DATE)
today = date.today()

start_date = st.sidebar.date_input(
    "From", value=max(earliest, today - timedelta(days=365 * 4)),
    min_value=earliest, max_value=today - timedelta(days=1),
)
end_date = st.sidebar.date_input(
    "To", value=today, min_value=earliest, max_value=today
)

st.sidebar.divider()

chosen = st.sidebar.multiselect(
    "Instruments",
    options=[i.code for i in ALL_INSTRUMENTS],
    default=list(DEFAULT_SELECTION),
    format_func=lambda c: BY_CODE[c].label,
    max_selections=charts.MAX_SERIES,
)

target = st.sidebar.selectbox(
    "Asset under test",
    options=[i.code for i in BINANCE_INSTRUMENTS
             if i.asset_class is AssetClass.CRYPTO],
    format_func=lambda c: BY_CODE[c].label,
)

window = st.sidebar.slider("Rolling window (days)", 30, 250, DEFAULT_ROLLING_WINDOW, 10)
quantile = st.sidebar.slider("Stress threshold (worst % of days)", 5, 25, 10, 5) / 100

st.sidebar.divider()
st.sidebar.caption(
    "**Method** — prices are joined only on days every source actually quoted, "
    "so weekend crypto moves are never matched against invented FX data. "
    "Stress days are defined by the currency basket alone, so the test cannot "
    "be circular."
)


# --- Guards ------------------------------------------------------------------

st.title("Is Bitcoin digital gold?")
st.caption(
    "Bitcoin is routinely called a store of value. This dashboard tests that "
    "claim against **real gold** and against the currencies investors actually "
    "flee to — measured on the days markets fall hardest."
)

if start_date >= end_date:
    st.error("The start date must fall before the end date.")
    st.stop()

if not chosen:
    st.info("Pick at least one instrument in the sidebar to begin.")
    st.stop()

if target not in chosen:
    chosen = [target, *chosen]

crypto_codes = tuple(c for c in chosen if BY_CODE[c].is_crypto_venue)
fx_codes = tuple(c for c in chosen if not BY_CODE[c].is_crypto_venue)

# Gold and the risk basket are always fetched: they are the yardsticks the
# verdict is measured against, whether or not the user charted them.
if GOLD_CODE not in crypto_codes:
    crypto_codes = (*crypto_codes, GOLD_CODE)
fx_codes = tuple(dict.fromkeys((*fx_codes, *RISK_PROXIES)))

start_iso, end_iso = start_date.isoformat(), end_date.isoformat()

try:
    with st.spinner("Fetching prices from Binance and the ECB…"):
        crypto = load_crypto(crypto_codes, start_iso, end_iso)
        fx = load_fx(fx_codes, start_iso, end_iso)
except ApiError as error:
    st.error(f"Could not load data — {error}")
    st.caption("Both APIs are public and unauthenticated; this is usually transient.")
    st.stop()

panel = align_panel([crypto, fx])

if panel.empty or len(panel) < 30:
    st.warning("Not enough overlapping trading days in this range. Widen the dates.")
    st.stop()

returns = daily_returns(panel)
labels = {c: BY_CODE[c].label for c in panel.columns}
displayed = [c for c in chosen if c in panel.columns]

# An inner join is only as long as its shortest series. PAXG, for instance, did
# not list until August 2020, so any window including gold silently begins
# there. Say so, rather than letting the axis quietly disagree with the picker.
actual_start, actual_end = panel.index[0].date(), panel.index[-1].date()
if actual_start > start_date:
    limiter = min(
        ((c, panel[c].first_valid_index()) for c in panel.columns),
        key=lambda pair: pair[1] if pair[1] is not None else pd.Timestamp.max,
    )
    st.info(
        f"Analysis window is **{actual_start} to {actual_end}** "
        f"({len(panel):,} shared trading days), not the {start_date} you asked "
        f"for: **{BY_CODE[limiter[0]].label}** has no history before "
        f"{actual_start}, and every series must be present on a day for that "
        "day to be comparable."
    )

verdict = assess_safe_haven(returns, target, GOLD_CODE, RISK_PROXIES, quantile)


# --- Headline ----------------------------------------------------------------

st.subheader("The verdict")

if verdict is None:
    st.warning("Too few observations in this window to judge. Widen the date range.")
else:
    tiles = st.columns(4)
    tiles[0].metric(f"{BY_CODE[target].label} behaves like", verdict.verdict_label)
    tiles[1].metric("…in falling markets (r)", f"{verdict.stress_correlation:+.2f}")
    tiles[2].metric("Real gold, same days (r)", f"{verdict.gold_stress_correlation:+.2f}")
    tiles[3].metric("Gap to gold", f"{verdict.gold_gap:+.2f}")

    st.caption(
        f"Measured over {verdict.observations:,} shared trading days, of which "
        f"{verdict.stress_observations:,} were the worst {quantile:.0%} for the "
        f"currency basket. A safe haven should sit at or below zero."
    )

st.divider()


# --- Figures -----------------------------------------------------------------

tab_verdict, tab_perf, tab_corr, tab_risk, tab_data = st.tabs(
    ["🎯 The test", "📈 Performance", "🔗 Correlation", "⚖️ Risk & reward", "🗂 Data"]
)

with tab_verdict:
    if verdict is None:
        st.info("No verdict available for this window.")
    else:
        st.plotly_chart(
            charts.stress_comparison_chart(
                BY_CODE[target].label,
                verdict.stress_correlation,
                verdict.gold_stress_correlation,
            ),
            use_container_width=True,
        )
        st.markdown(
            f"""
**How to read this.** Both bars cover the same {verdict.stress_observations:,}
worst days, so they are directly comparable. A bar at or below zero marks a
genuine safe haven — the asset held its own precisely when the market did not.
A tall positive bar marks a risk asset that fell *with* everything else, which
is the opposite of what a store of value is supposed to do.

**Why the level, not the change.** Restricting to the worst decile narrows the
spread of the basket, and a correlation measured over a narrowed range is
mechanically pulled toward zero. Almost any asset therefore looks like it
"decouples" under stress. Judging the stressed correlation against a fixed
threshold, and against gold on the very same days, avoids that trap.
"""
        )

with tab_perf:
    st.plotly_chart(
        charts.performance_chart(rebase_to_100(panel[displayed]), labels),
        use_container_width=True,
    )
    stats = summary_table(panel[displayed])
    st.dataframe(
        stats.rename(index=labels).style.format({
            "Annualised Return": "{:+.1%}",
            "Annualised Volatility": "{:.1%}",
            "Max Drawdown": "{:.1%}",
        }),
        use_container_width=True,
    )

with tab_corr:
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(
            charts.correlation_heatmap(correlation_matrix(returns[displayed]), labels),
            use_container_width=True,
        )
    with right:
        peers = [c for c in displayed if c != target]
        rolled = rolling_correlation(returns, target, peers, window)
        if rolled.empty:
            st.info("Add another instrument to see rolling correlation.")
        else:
            st.plotly_chart(
                charts.rolling_correlation_chart(
                    rolled, BY_CODE[target].label, labels, window
                ),
                use_container_width=True,
            )

with tab_risk:
    st.plotly_chart(
        charts.risk_return_scatter(
            summary_table(panel[displayed]),
            {c: group_of(c) for c in displayed},
            labels,
        ),
        use_container_width=True,
    )
    st.caption(
        "Up is more reward, right is more risk. A store of value should sit "
        "toward the left; Bitcoin's position on this axis is the whole argument."
    )

with tab_data:
    table = panel[displayed].rename(columns=labels)
    st.dataframe(table, use_container_width=True)
    st.download_button(
        "Download aligned prices (CSV)",
        table.to_csv().encode("utf-8"),
        file_name=f"digital_gold_{start_iso}_{end_iso}.csv",
        mime="text/csv",
    )
    st.caption(
        f"{len(table):,} rows — one per day on which every selected source "
        "quoted a price. Sources: Binance public REST API; European Central "
        "Bank reference rates via Frankfurter."
    )
