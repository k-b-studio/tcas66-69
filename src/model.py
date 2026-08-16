"""Forecasting program-level min scores for TCAS70 (R5).

**Read this before trusting anything below.** There are four observations per
program. Leave-last-year-out leaves three points to fit an intercept and a
slope — two parameters, one residual degree of freedom. The per-program fit is
very close to saturated. Partial pooling is not a refinement here; it is the
only thing that makes per-program slopes legitimate at all, and the honest
interval is wide.

The baselines are therefore not a formality. With n = 4, last-value-carried-
forward is a serious competitor, and if it wins it is what ships.

Model choice: the spec asks for ``numpyro`` or ``pymc``. Neither is installed
in this environment, so this uses the sanctioned fallback — ``statsmodels``
``MixedLM`` with a random intercept and random slope on year, partially pooling
program trends toward the population mean, with faculty as a fixed effect.
That is a two-level approximation to the spec's three-level design; statsmodels
cannot cleanly express random slopes nested at two levels.

Covariate note: a genuine TCAS70 forecast cannot use TCAS70's applications or
admits — they do not exist yet. Contemporaneous covariates would make this a
back-fit, not a forecast. Any covariate model here therefore uses **lagged**
values, which costs a year of panel depth (4 points becomes 3).
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from src.load import PROCESSED, chula_panel, load_all
from src.normalize import cohort_difficulty_index

YEARS = (66, 67, 68, 69)
TARGET_YEAR = 70
BASE_YEAR = 66

#: Reported for every method so a win is never assumed.
BASELINES = ("lvcf", "program_mean", "program_ols")


# --- data ----------------------------------------------------------------

def build_panel(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """The 48-code balanced panel plus modelling features."""
    frame = df if df is not None else load_all()
    panel = chula_panel(frame).copy()

    difficulty = cohort_difficulty_index()
    wide = difficulty.pivot(index="tcas_year", columns="exam_family",
                            values="mean_index")
    panel["diff_alevel"] = panel["year"].map(wide["A-Level"])
    panel["diff_tgat"] = panel["year"].map(wide["TGAT/TPAT"])

    panel = panel.sort_values(["code", "year"])
    for col in ("min_score", "applied", "passed", "apps_per_admit"):
        panel[f"prev_{col}"] = panel.groupby("code")[col].shift(1)

    panel["year_c"] = panel["year"] - BASE_YEAR
    return panel.reset_index(drop=True)


# --- baselines -----------------------------------------------------------

def baseline_lvcf(train: pd.DataFrame, target_year: int) -> pd.Series:
    """Last value carried forward. The one to beat."""
    last = train.sort_values("year").groupby("code")["min_score"].last()
    return last.rename("pred")


def baseline_program_mean(train: pd.DataFrame, target_year: int) -> pd.Series:
    return train.groupby("code")["min_score"].mean().rename("pred")


def baseline_program_ols(train: pd.DataFrame, target_year: int) -> pd.Series:
    """Per-program least squares on year — no pooling at all.

    With three training points this fits two parameters from three
    observations. It is included precisely to show what unpooled estimation
    does at this sample size.
    """
    preds = {}
    for code, g in train.groupby("code"):
        g = g.dropna(subset=["min_score"])
        if len(g) < 2:
            preds[code] = g["min_score"].mean()
            continue
        slope, intercept = np.polyfit(g["year_c"], g["min_score"], 1)
        preds[code] = intercept + slope * (target_year - BASE_YEAR)
    return pd.Series(preds, name="pred")


# --- hierarchical model --------------------------------------------------

_FORMULA = "min_score ~ year_c + C(faculty)"


def fit_hierarchical(train: pd.DataFrame, random_slope: bool = True):
    """Partially-pooled linear trend.

    ``random_slope=True`` gives each program its own intercept *and* slope,
    shrunk toward the population values — the spec's primary model.
    ``random_slope=False`` keeps a single global slope and pools only the
    level. Comparing the two isolates whether per-program trend estimation
    earns its keep at n = 4, which is the whole question.
    """
    data = train.dropna(subset=["min_score"]).copy()
    model = smf.mixedlm(
        _FORMULA, data=data, groups=data["code"],
        re_formula="~year_c" if random_slope else "~1",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return model.fit(method="lbfgs", maxiter=2000)


def predict_hierarchical(result, train: pd.DataFrame, target_year: int) -> pd.Series:
    """Fixed effects at the target year plus each program's shrunken BLUP."""
    year_c = target_year - BASE_YEAR
    codes = train["code"].unique()
    meta = train.groupby("code").agg(faculty=("faculty", "first"))

    design = pd.DataFrame({
        "code": codes,
        "year_c": year_c,
        "faculty": meta.loc[codes, "faculty"].values,
        "min_score": 0.0,
    })
    exog = smf.mixedlm(
        _FORMULA, data=design, groups=design["code"], re_formula="~1",
    ).exog
    fitted = exog @ result.fe_params.values

    preds = {}
    for i, code in enumerate(design["code"]):
        re = result.random_effects.get(code)
        adj = 0.0
        if re is not None:
            values = np.asarray(re)
            adj = values[0] + (values[1] * year_c if len(values) > 1 else 0.0)
        preds[code] = fitted[i] + adj
    return pd.Series(preds, name="pred")


# --- evaluation ----------------------------------------------------------

def _score(truth: pd.Series, pred: pd.Series) -> dict[str, float]:
    joined = pd.concat([truth.rename("y"), pred.rename("p")], axis=1).dropna()
    err = joined["p"] - joined["y"]
    return {
        "MAE": err.abs().mean(),
        "RMSE": float(np.sqrt((err ** 2).mean())),
        "bias": err.mean(),
        "n": len(joined),
    }


def backtest(panel: pd.DataFrame, holdout_year: int = 69) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Leave-last-year-out: fit on 66–68, predict 69, score every method.

    Returns (summary table, per-faculty MAE table, signed errors of the
    hierarchical model — used to calibrate the shipped intervals).
    """
    train = panel[panel["year"] < holdout_year]
    test = panel[panel["year"] == holdout_year].set_index("code")
    truth = test["min_score"]

    preds = {
        "lvcf": baseline_lvcf(train, holdout_year),
        "program_mean": baseline_program_mean(train, holdout_year),
        "program_ols": baseline_program_ols(train, holdout_year),
    }
    result = fit_hierarchical(train, random_slope=True)
    preds["hierarchical"] = predict_hierarchical(result, train, holdout_year)
    flat = fit_hierarchical(train, random_slope=False)
    preds["hier_no_slope"] = predict_hierarchical(flat, train, holdout_year)

    summary = pd.DataFrame({k: _score(truth, v) for k, v in preds.items()}).T
    summary = summary.sort_values("MAE")

    faculty = test["faculty"]
    rows = {}
    for name, pred in preds.items():
        err = (pred.reindex(truth.index) - truth).abs()
        rows[name] = err.groupby(faculty).mean()
    per_faculty = pd.DataFrame(rows).round(2)
    per_faculty["n"] = truth.groupby(faculty).size()

    signed = (preds["hierarchical"].reindex(truth.index) - truth).dropna()
    return summary.round(3), per_faculty, signed


# --- forecast ------------------------------------------------------------

def _predict(method: str, train: pd.DataFrame, target_year: int) -> pd.Series:
    builders = {
        "lvcf": baseline_lvcf,
        "program_mean": baseline_program_mean,
        "program_ols": baseline_program_ols,
    }
    if method in builders:
        return builders[method](train, target_year)
    result = fit_hierarchical(train, random_slope=(method == "hierarchical"))
    return predict_hierarchical(result, train, target_year)


def calibration_errors(panel: pd.DataFrame, method: str) -> pd.Series:
    """Pooled one-year-ahead errors from every origin the panel allows.

    Calibrating the interval on the single 68→69 transition would tie it to one
    year that happened to fall. Rolling the origin gives 67→68 as well, so the
    interval reflects two different year transitions rather than one. It is
    still only two, which is why the resulting band is wide and should be.
    """
    chunks = []
    for holdout in (68, 69):
        train = panel[panel["year"] < holdout]
        test = panel[panel["year"] == holdout].set_index("code")
        pred = _predict(method, train, holdout).reindex(test.index)
        chunks.append((pred - test["min_score"]).dropna())
    return pd.concat(chunks)


def forecast(
    panel: pd.DataFrame,
    errors: pd.Series,
    winner: str,
    target_year: int = TARGET_YEAR,
) -> pd.DataFrame:
    """Refit on all four years and predict `target_year`.

    Intervals are **empirical**: quantiles of the shipped method's pooled
    one-year-ahead error distribution (see :func:`calibration_errors`), not the
    model's own variance estimate. With four points per program the model's
    internal uncertainty is not credible, whereas the rolling-origin errors are
    a demonstrated out-of-sample record.

    The band is wide. That is the correct answer at n = 4, not a defect to tune
    away — and it is still optimistic, because it is calibrated on two year
    transitions.
    """
    point = _predict(winner, panel, target_year)

    q = {
        "lo80": np.quantile(errors, 0.10),
        "hi80": np.quantile(errors, 0.90),
        "lo95": np.quantile(errors, 0.025),
        "hi95": np.quantile(errors, 0.975),
    }

    meta = panel.sort_values("year").groupby("code").agg(
        program=("program", "last"), faculty=("faculty", "last")
    )
    out = meta.join(point.rename("point"))
    # Errors are (pred - truth); subtract to invert into a truth interval.
    out["lo80"] = out["point"] - q["hi80"]
    out["hi80"] = out["point"] - q["lo80"]
    out["lo95"] = out["point"] - q["hi95"]
    out["hi95"] = out["point"] - q["lo95"]
    out["model"] = winner
    return out.reset_index()


def write_forecast(forecast_df: pd.DataFrame, beat_baseline: bool,
                   outdir: Path = PROCESSED) -> Path:
    out = forecast_df.copy()
    out["beat_baseline"] = beat_baseline
    cols = ["code", "program", "faculty", "point", "lo80", "hi80",
            "lo95", "hi95", "model", "beat_baseline"]
    path = outdir / "forecast_tcas70.csv"
    out[cols].round(4).to_csv(path, index=False)
    return path


METHODS = ("lvcf", "program_mean", "program_ols", "hierarchical", "hier_no_slope")


def rolling_backtest(panel: pd.DataFrame) -> pd.DataFrame:
    """Score every method at every one-year-ahead origin the panel allows.

    The spec asks for leave-last-year-out, which is a single 68→69 transition.
    That turned out to be a *falling* year, and the sign of every method's bias
    flips between origins (67→68: −0.4; 68→69: +3.2), so a single holdout can
    pick a winner that owes its win to which way that one year happened to
    move. Rolling the origin doubles the evidence to two transitions.

    Caveat: the 67→68 origin trains on only two years, which is why the
    trend-fitting methods look even worse there than they do at 68→69.
    """
    rows = []
    for holdout in (68, 69):
        train = panel[panel["year"] < holdout]
        test = panel[panel["year"] == holdout].set_index("code")
        truth = test["min_score"]
        for method in METHODS:
            pred = _predict(method, train, holdout).reindex(truth.index)
            stats = _score(truth, pred)
            rows.append({"origin": f"{holdout - 1}→{holdout}", "method": method,
                         "train_years": train["year"].nunique(), **stats})
    long = pd.DataFrame(rows)
    pooled = (
        long.groupby("method")
        .apply(lambda g: pd.Series({
            "MAE": np.average(g["MAE"], weights=g["n"]),
            "RMSE": float(np.sqrt(np.average(g["RMSE"] ** 2, weights=g["n"]))),
            "n": g["n"].sum(),
        }), include_groups=False)
        .sort_values("MAE")
    )
    return long, pooled.round(3)


def compare_top_two(panel: pd.DataFrame, a: str, b: str, holdout_year: int = 69) -> dict:
    """Paired test on absolute errors — is the gap between two methods real?

    A 0.5-point MAE gap across 48 programs is easy to over-read. This reports
    whether the difference survives a paired test and a bootstrap.
    """
    from scipy import stats

    train = panel[panel["year"] < holdout_year]
    test = panel[panel["year"] == holdout_year].set_index("code")
    truth = test["min_score"]

    err_a = (_predict(a, train, holdout_year).reindex(truth.index) - truth).abs()
    err_b = (_predict(b, train, holdout_year).reindex(truth.index) - truth).abs()
    diff = (err_a - err_b).dropna()

    rng = np.random.default_rng(0)
    boot = [rng.choice(diff, len(diff)).mean() for _ in range(5000)]
    return {
        f"MAE {a}": err_a.mean(),
        f"MAE {b}": err_b.mean(),
        "difference": diff.mean(),
        "paired t p": stats.ttest_rel(err_a, err_b).pvalue,
        "wilcoxon p": stats.wilcoxon(err_a, err_b).pvalue,
        "boot lo": float(np.percentile(boot, 2.5)),
        "boot hi": float(np.percentile(boot, 97.5)),
        f"{b} better on": int((diff > 0).sum()),
        "of": len(diff),
    }


def run(verbose: bool = True) -> dict:
    """Full pipeline: panel -> backtest -> pick winner -> forecast -> csv."""
    panel = build_panel()
    summary, per_faculty, _ = backtest(panel)
    long, pooled = rolling_backtest(panel)

    best_baseline = summary.loc[list(BASELINES), "MAE"].min()
    hier_mae = summary.loc["hierarchical", "MAE"]
    beat = bool(hier_mae < best_baseline)

    # Selection uses the two-origin evidence, not the single holdout. On the
    # spec's leave-last-year-out alone the winner is program_mean, but that
    # method swings from best (4.89) to near-worst (7.13) depending on which
    # way the held-out year moved. LVCF is the only method that is stable at
    # both origins, and it wins pooled.
    winner = "hierarchical" if beat else str(pooled.index[0])
    errors = calibration_errors(panel, winner)

    fc = forecast(panel, errors, winner)
    path = write_forecast(fc, beat)

    if verbose:
        print(summary.to_string(), "\n")
        print(f"best baseline MAE : {best_baseline:.3f}  ({summary.loc[list(BASELINES),'MAE'].idxmin()})")
        print(f"hierarchical MAE  : {hier_mae:.3f}")
        print(f"hierarchical beats baselines: {beat}")
        print("\npooled over both origins:")
        print(pooled.to_string())
        print(f"\nshipping: {winner} -> {path.name}")
        width = fc["hi80"].sub(fc["lo80"]).mean()
        print(f"mean 80% interval width: {width:.1f} points")
    return {"summary": summary, "per_faculty": per_faculty, "forecast": fc,
            "winner": winner, "beat": beat, "path": path, "errors": errors,
            "rolling_long": long, "rolling_pooled": pooled}


if __name__ == "__main__":
    run()
