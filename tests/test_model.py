"""Tests for the forecasting layer (R5).

The important one is ``test_hierarchical_does_not_beat_baselines``: it pins the
project's actual finding rather than a hoped-for one. If a future change makes
the model win, that test fails and the claim in `reports/findings.md` has to be
rewritten — which is the correct outcome, not a nuisance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import src.model as M
from src.load import PROCESSED


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return M.build_panel()


@pytest.fixture(scope="module")
def result(panel):
    return M.run(verbose=False)


# --- panel ---------------------------------------------------------------

def test_panel_is_balanced(panel) -> None:
    assert len(panel) == 48 * 4
    assert panel["code"].nunique() == 48
    assert set(panel["year"]) == {66, 67, 68, 69}


def test_panel_carries_no_seats(panel) -> None:
    """Trap 1: seats must never reach the model."""
    assert not [c for c in panel.columns if "seat" in c.lower()]


def test_panel_has_difficulty_and_lags(panel) -> None:
    assert panel["diff_alevel"].notna().all()
    assert panel["diff_tgat"].notna().all()
    # Lags are undefined in the first year by construction.
    assert panel[panel["year"] == 66]["prev_min_score"].isna().all()
    assert panel[panel["year"] > 66]["prev_min_score"].notna().all()


# --- baselines -----------------------------------------------------------

@pytest.mark.parametrize("name", M.BASELINES)
def test_baselines_predict_every_program(panel, name: str) -> None:
    train = panel[panel["year"] < 69]
    pred = M._predict(name, train, 69)
    assert len(pred) == 48
    assert pred.notna().all()


def test_lvcf_is_literally_the_last_value(panel) -> None:
    train = panel[panel["year"] < 69]
    pred = M.baseline_lvcf(train, 69)
    expected = train[train["year"] == 68].set_index("code")["min_score"]
    pd.testing.assert_series_equal(
        pred.sort_index(), expected.sort_index(), check_names=False
    )


# --- backtest ------------------------------------------------------------

def test_backtest_scores_every_method(panel) -> None:
    summary, per_faculty, errors = M.backtest(panel)
    assert set(summary.index) == set(M.METHODS)
    assert (summary["n"] == 48).all()
    assert len(errors) == 48
    assert per_faculty["n"].sum() == 48


def test_hierarchical_does_not_beat_baselines(panel) -> None:
    """The project's actual result, pinned.

    With n = 4 the partially-pooled trend model loses to trivial baselines.
    Reporting that honestly is worth more than a model that wins by
    construction.
    """
    summary, _, _ = M.backtest(panel)
    best_baseline = summary.loc[list(M.BASELINES), "MAE"].min()
    assert summary.loc["hierarchical", "MAE"] > best_baseline


def test_pooling_beats_no_pooling(panel) -> None:
    """Shrinkage does help — just not enough to make slopes worth having.

    The hierarchical model beats unpooled per-program OLS at both origins,
    which is exactly what partial pooling is for.
    """
    long, _ = M.rolling_backtest(panel)
    wide = long.pivot(index="method", columns="origin", values="MAE")
    assert (wide.loc["hierarchical"] < wide.loc["program_ols"]).all()


def test_trend_freedom_costs_accuracy_at_the_spec_holdout(panel) -> None:
    """Ordering at leave-last-year-out: more trend freedom, worse forecast."""
    summary, _, _ = M.backtest(panel)
    mae = summary["MAE"]
    assert mae["program_ols"] > mae["hierarchical"] > mae["hier_no_slope"] > mae["program_mean"]


def test_rolling_backtest_uses_two_origins(panel) -> None:
    long, pooled = M.rolling_backtest(panel)
    assert set(long["origin"]) == {"67→68", "68→69"}
    assert (pooled["n"] == 96).all()
    assert set(pooled.index) == set(M.METHODS)


def test_bias_flips_sign_between_origins(panel) -> None:
    """Why selection uses two origins, not one.

    Every method over-predicts the falling 68→69 year and under-predicts the
    rising 67→68 one. A single holdout would bake that year's direction into
    both the winner and the interval.
    """
    long, _ = M.rolling_backtest(panel)
    bias = long.pivot(index="method", columns="origin", values="bias")
    assert (bias["67→68"] < 0).all()
    assert (bias["68→69"] > 0).all()


# --- forecast ------------------------------------------------------------

def test_forecast_csv_shape_and_columns(result) -> None:
    out = pd.read_csv(PROCESSED / "forecast_tcas70.csv")
    assert list(out.columns) == [
        "code", "program", "faculty", "point", "lo80", "hi80",
        "lo95", "hi95", "model", "beat_baseline",
    ]
    assert len(out) == 48
    assert out["code"].nunique() == 48


def test_every_row_carries_a_nested_interval(result) -> None:
    out = pd.read_csv(PROCESSED / "forecast_tcas70.csv")
    assert out[["point", "lo80", "hi80", "lo95", "hi95"]].notna().all().all()
    assert (out["lo95"] <= out["lo80"]).all()
    assert (out["lo80"] <= out["point"]).all()
    assert (out["point"] <= out["hi80"]).all()
    assert (out["hi80"] <= out["hi95"]).all()


def test_interval_is_honestly_wide(result) -> None:
    """A narrow band at n = 4 would mean noise was absorbed as signal."""
    out = pd.read_csv(PROCESSED / "forecast_tcas70.csv")
    assert (out["hi80"] - out["lo80"]).mean() > 10
    assert (out["hi95"] - out["lo95"]).mean() > 20


def test_shipped_model_is_recorded_and_flag_is_false(result) -> None:
    out = pd.read_csv(PROCESSED / "forecast_tcas70.csv")
    assert out["model"].nunique() == 1
    assert out["model"].iloc[0] == result["winner"]
    # The hierarchical model lost, so this flag must say so.
    assert not out["beat_baseline"].any()


def test_calibration_pools_both_origins(panel) -> None:
    errors = M.calibration_errors(panel, "lvcf")
    assert len(errors) == 96
