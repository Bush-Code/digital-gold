"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : digital_gold.analysis.correlation
  Identifier  : 7ff65b6d-358b-48f3-9511-c632d674759a
  Created     : 2026-09-05
  Purpose     : The co-movement evidence that answers "is Bitcoin digital gold?"
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

MIN_OBSERVATIONS = 30
DEFAULT_ROLLING_WINDOW = 90
DEFAULT_STRESS_QUANTILE = 0.10

# Above this stressed correlation an asset is moving *with* the market, not
# sheltering from it. 0.3 is the conventional weak/moderate dividing line.
DIVERSIFIER_THRESHOLD = 0.30


@dataclass(frozen=True, slots=True)
class SafeHavenVerdict:
    """The finding, in a form the UI can render without re-deriving anything."""

    calm_correlation: float
    stress_correlation: float
    gold_correlation: float
    gold_stress_correlation: float
    observations: int
    stress_observations: int

    @property
    def behaves_like_gold(self) -> bool:
        """True when the asset decouples from risk exactly when it matters.

        Baur & Lucey's definition: a safe haven is uncorrelated or negatively
        correlated with risk assets *during market stress* -- not on average.
        An asset that only diversifies in calm markets is a diversifier, not a
        haven, which is precisely the distinction this project tests.
        """
        return self.stress_correlation <= 0.0

    @property
    def verdict_label(self) -> str:
        """Classify on the stress correlation's LEVEL, not on calm-vs-stress.

        Conditioning on the worst decile truncates the range of the risk
        basket, and a correlation measured over a restricted range is
        attenuated purely as an artefact of that truncation. Comparing the
        calm and stressed figures would therefore flag almost any asset as
        "decoupling" -- including one that amplifies the market. Judging the
        stressed correlation against fixed thresholds avoids that trap.
        """
        if self.stress_correlation <= 0.0:
            return "Safe Haven"
        if self.stress_correlation < DIVERSIFIER_THRESHOLD:
            return "Diversifier"
        return "Risk Asset"

    @property
    def gold_gap(self) -> float:
        """How far the asset sits from real gold on the same stressed days.

        Both figures come from the identical subsample, so this comparison is
        free of the range-restriction bias described above. It is the most
        direct answer the data can give to "is Bitcoin digital gold?".
        """
        return self.stress_correlation - self.gold_stress_correlation


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Pairwise Pearson correlation across every instrument."""
    if returns.empty or len(returns) < 2:
        return pd.DataFrame()
    return returns.corr()


def rolling_correlation(
    returns: pd.DataFrame,
    target: str,
    others: list[str],
    window: int = DEFAULT_ROLLING_WINDOW,
) -> pd.DataFrame:
    """Correlation of `target` against each of `others` through time.

    A single full-sample number hides regime change; this is what shows whether
    Bitcoin's relationship with gold is stable or drifting.
    """
    available = [c for c in others if c in returns.columns and c != target]
    if returns.empty or target not in returns.columns or not available:
        return pd.DataFrame()

    window = max(2, min(window, len(returns)))
    rolled = {
        other: returns[target].rolling(window).corr(returns[other])
        for other in available
    }
    return pd.DataFrame(rolled).dropna(how="all")


def stress_mask(
    returns: pd.DataFrame,
    risk_proxies: list[str],
    quantile: float = DEFAULT_STRESS_QUANTILE,
) -> pd.Series:
    """Flag the worst days for a basket of risk assets.

    Stress is defined by assets *other than* Bitcoin, so the test cannot be
    circular: we are asking how BTC behaves when the wider market is falling,
    not when BTC itself is falling.
    """
    present = [c for c in risk_proxies if c in returns.columns]
    if returns.empty or not present:
        return pd.Series(False, index=returns.index)

    basket = returns[present].mean(axis=1)
    threshold = basket.quantile(quantile)
    return basket <= threshold


def assess_safe_haven(
    returns: pd.DataFrame,
    target: str,
    gold: str,
    risk_proxies: list[str],
    quantile: float = DEFAULT_STRESS_QUANTILE,
) -> SafeHavenVerdict | None:
    """Compare `target`'s link to risk in calm vs stressed markets.

    Returns None when there is too little data to say anything honest.
    """
    present = [c for c in risk_proxies if c in returns.columns]
    if returns.empty or target not in returns.columns or not present:
        return None
    if len(returns) < MIN_OBSERVATIONS:
        return None

    basket = returns[present].mean(axis=1)
    stressed = stress_mask(returns, present, quantile)

    calm_slice = returns.loc[~stressed, target]
    stress_slice = returns.loc[stressed, target]

    if len(stress_slice) < 2 or len(calm_slice) < 2:
        return None

    has_gold = gold in returns.columns and gold != target
    gold_corr = float(returns[target].corr(returns[gold])) if has_gold else float("nan")

    # Gold's own stressed correlation is the yardstick: it is what "behaving
    # like gold" numerically means, measured on the very same days.
    gold_stress_corr = (
        float(returns.loc[stressed, gold].corr(basket.loc[stressed]))
        if has_gold
        else float("nan")
    )

    return SafeHavenVerdict(
        calm_correlation=float(calm_slice.corr(basket.loc[~stressed])),
        stress_correlation=float(stress_slice.corr(basket.loc[stressed])),
        gold_correlation=gold_corr,
        gold_stress_correlation=gold_stress_corr,
        observations=int(len(returns)),
        stress_observations=int(stressed.sum()),
    )
