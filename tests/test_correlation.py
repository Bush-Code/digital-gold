"""
================================================================================
  BUSH.AI  |  PROPRIETARY
--------------------------------------------------------------------------------
  Module      : tests.test_correlation
  Identifier  : 62ac954c-5e2f-414f-a08d-51c3695207cf
  Created     : 2026-09-05
  Purpose     : Prove the safe-haven test separates havens from risk assets.
================================================================================
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from digital_gold.analysis.correlation import (
    assess_safe_haven,
    correlation_matrix,
    rolling_correlation,
    stress_mask,
)


def _returns(n: int = 300, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    risk = rng.normal(0, 0.01, n)
    return pd.DataFrame(
        {
            "AUD": risk,
            "EUR": risk * 0.8 + rng.normal(0, 0.002, n),
            "HAVEN": -risk * 0.9 + rng.normal(0, 0.002, n),
            "FOLLOWER": risk * 1.5 + rng.normal(0, 0.002, n),
            "PAXGUSDT": rng.normal(0, 0.005, n),
        },
        index=pd.bdate_range("2024-01-01", periods=n),
    )


def test_correlation_matrix_is_square_and_unit_diagonal() -> None:
    matrix = correlation_matrix(_returns())

    assert matrix.shape == (5, 5)
    assert np.allclose(np.diag(matrix), 1.0)


def test_correlation_matrix_on_insufficient_data_is_empty() -> None:
    assert correlation_matrix(pd.DataFrame()).empty
    assert correlation_matrix(pd.DataFrame({"A": [0.1]})).empty


def test_stress_mask_selects_the_worst_decile() -> None:
    returns = _returns(n=200)

    mask = stress_mask(returns, ["AUD", "EUR"], quantile=0.10)

    assert mask.sum() == pytest.approx(20, abs=2)
    stressed_mean = returns.loc[mask, "AUD"].mean()
    calm_mean = returns.loc[~mask, "AUD"].mean()
    assert stressed_mean < calm_mean


def test_stress_mask_without_proxies_flags_nothing() -> None:
    assert not stress_mask(_returns(), ["MISSING"]).any()


def test_an_inverse_asset_is_labelled_a_safe_haven() -> None:
    verdict = assess_safe_haven(_returns(), "HAVEN", "PAXGUSDT", ["AUD", "EUR"])

    assert verdict is not None
    assert verdict.stress_correlation < 0
    assert verdict.behaves_like_gold
    assert verdict.verdict_label == "Safe Haven"


def test_an_amplifying_asset_is_labelled_a_risk_asset() -> None:
    verdict = assess_safe_haven(_returns(), "FOLLOWER", "PAXGUSDT", ["AUD", "EUR"])

    assert verdict is not None
    assert verdict.stress_correlation > 0
    assert not verdict.behaves_like_gold
    assert verdict.verdict_label == "Risk Asset"


def test_stress_is_defined_without_the_target_so_the_test_is_not_circular() -> None:
    """Stress days must come from the risk basket alone."""
    returns = _returns()

    from_basket = stress_mask(returns, ["AUD", "EUR"])
    with_target = stress_mask(returns[["AUD", "EUR"]], ["AUD", "EUR"])

    pd.testing.assert_series_equal(from_basket, with_target)


def test_too_few_observations_returns_none_rather_than_a_guess() -> None:
    tiny = _returns(n=10)

    assert assess_safe_haven(tiny, "HAVEN", "PAXGUSDT", ["AUD"]) is None


def test_missing_target_returns_none() -> None:
    assert assess_safe_haven(_returns(), "ABSENT", "PAXGUSDT", ["AUD"]) is None


def test_rolling_correlation_respects_its_window() -> None:
    returns = _returns(n=200)

    rolled = rolling_correlation(returns, "FOLLOWER", ["AUD", "HAVEN"], window=60)

    assert list(rolled.columns) == ["AUD", "HAVEN"]
    assert rolled["AUD"].mean() > 0.5
    assert rolled["HAVEN"].mean() < 0


def test_rolling_correlation_excludes_the_target_itself() -> None:
    rolled = rolling_correlation(_returns(), "AUD", ["AUD", "HAVEN"])

    assert "AUD" not in rolled.columns


def test_rolling_correlation_with_no_valid_peers_is_empty() -> None:
    assert rolling_correlation(_returns(), "AUD", ["MISSING"]).empty


def test_threshold_separates_diversifier_from_risk_asset() -> None:
    """The label must turn on the stressed level, at the documented cut-off."""
    from digital_gold.analysis.correlation import (
        DIVERSIFIER_THRESHOLD,
        SafeHavenVerdict,
    )

    def _verdict(stress: float) -> SafeHavenVerdict:
        return SafeHavenVerdict(
            calm_correlation=0.9,
            stress_correlation=stress,
            gold_correlation=0.0,
            gold_stress_correlation=0.0,
            observations=300,
            stress_observations=30,
        )

    assert _verdict(-0.10).verdict_label == "Safe Haven"
    assert _verdict(0.0).verdict_label == "Safe Haven"
    assert _verdict(DIVERSIFIER_THRESHOLD - 0.01).verdict_label == "Diversifier"
    assert _verdict(DIVERSIFIER_THRESHOLD).verdict_label == "Risk Asset"
    assert _verdict(0.85).verdict_label == "Risk Asset"


def test_amplifying_asset_is_not_mislabelled_despite_range_restriction() -> None:
    """Regression: truncating to the worst decile attenuates correlation, which
    previously made an amplifying asset look like a diversifier."""
    verdict = assess_safe_haven(_returns(), "FOLLOWER", "PAXGUSDT", ["AUD", "EUR"])

    assert verdict is not None
    assert verdict.stress_correlation < verdict.calm_correlation, "attenuation is real"
    assert verdict.verdict_label == "Risk Asset", "but must not change the label"


def test_gold_gap_is_measured_on_the_same_stressed_days() -> None:
    verdict = assess_safe_haven(_returns(), "FOLLOWER", "PAXGUSDT", ["AUD", "EUR"])

    assert verdict is not None
    assert verdict.gold_gap == pytest.approx(
        verdict.stress_correlation - verdict.gold_stress_correlation
    )
    assert verdict.gold_gap > 0, "a risk asset must sit above gold"
