"""Regression tests for the three data traps, plus the sanity targets.

These are the tests that stop a casual analysis from being silently wrong.
Every trap here was verified empirically against the source xlsx before being
written down; a failure means the loader changed, not that the test is stale.

Each score-based test states its filter explicitly, because the level (though
not the shape) of every national figure depends on it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.load import (
    CHULA,
    EXPECTED_NATIONAL_KEY_COLLISIONS,
    EXPECTED_ROWS,
    PROCESSED,
    ROW_KEY,
    YEARS,
    chula,
    load_all,
    reconstructed_seats,
    stable_chula_codes,
    validate,
)


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return load_all()


@pytest.fixture(scope="module")
def ch(df: pd.DataFrame) -> pd.DataFrame:
    return chula(df)


# --------------------------------------------------------------------------
# Loader invariants
# --------------------------------------------------------------------------

@pytest.mark.parametrize("year", YEARS)
def test_row_counts_match_source(df: pd.DataFrame, year: int) -> None:
    assert len(df[df["year"] == year]) == EXPECTED_ROWS[year]


def test_validate_passes(df: pd.DataFrame) -> None:
    validate(df)


def test_schema_is_stable(df: pd.DataFrame) -> None:
    from src.load import SCHEMA

    assert list(df.columns) == [*SCHEMA, "row_id"]


def test_tcas66_has_no_second_pass(df: pd.DataFrame) -> None:
    """ทปอ. ran Double Sorting in 66 but never published it."""
    y66 = df[df["year"] == 66]
    assert y66["min_score_ds"].isna().all()
    assert y66["passed_ds"].isna().all()


# --------------------------------------------------------------------------
# Grain
# --------------------------------------------------------------------------

@pytest.mark.parametrize("year", YEARS)
def test_row_key_unique_within_chula(ch: pd.DataFrame, year: int) -> None:
    assert not ch[ch["year"] == year].duplicated(subset=ROW_KEY).any()


@pytest.mark.parametrize("year", YEARS)
def test_national_key_collisions_are_known(df: pd.DataFrame, year: int) -> None:
    """Nationally the key is NOT unique. Guard the counts; never drop the rows."""
    collisions = df[df["year"] == year].duplicated(subset=ROW_KEY).sum()
    assert collisions == EXPECTED_NATIONAL_KEY_COLLISIONS[year]


def test_row_id_is_unique_per_year(df: pd.DataFrame) -> None:
    """The positional fallback identity for colliding national rows."""
    assert not df.duplicated(subset=["year", "row_id"]).any()


# --------------------------------------------------------------------------
# Trap 0 — university matching
# --------------------------------------------------------------------------

def test_chula_match_is_exact_not_substring(df: pd.DataFrame) -> None:
    """`contains("จุฬา")` also matches มหาจุฬาลงกรณ + ราชวิทยาลัยจุฬาภรณ์.

    Using it would report TCAS69 applications as 49,976 instead of 48,615.
    """
    y69 = df[df["year"] == 69]
    substring = y69[y69["univ"].str.contains("จุฬา", na=False)]
    assert substring["univ"].nunique() == 3
    assert chula(y69)["applied"].sum() == 48_615
    assert substring["applied"].sum() == 49_976


# --------------------------------------------------------------------------
# Trap 1 — seats cannot be summed
# --------------------------------------------------------------------------

def test_raw_seat_sum_is_inflated(ch: pd.DataFrame) -> None:
    c69 = ch[ch["year"] == 69]
    assert c69["seats"].sum() == 7_639
    assert c69["seats"].sum() > 1.9 * c69["passed"].sum()


def test_groupby_first_discards_a_real_pool(ch: pd.DataFrame) -> None:
    """`groupby(code).first()` is wrong, and here is the row that proves it.

    Code 10010122904301A (อักษรศาสตร์) holds two distinct pools, 20 and 209.
    `first()` keeps 20 and throws away 209.
    """
    c69 = ch[ch["year"] == 69]
    pools = c69[c69["code"] == "10010122904301A"]["seats"]
    assert {20.0, 209.0} <= set(pools)
    assert c69.groupby("code")["seats"].first().sum() == 2_728


@pytest.mark.parametrize(
    ("year", "expected"),
    [(66, 4_036), (67, 3_837), (68, 3_815), (69, 3_847)],
)
def test_reconstructed_seats(ch: pd.DataFrame, year: int, expected: float) -> None:
    assert reconstructed_seats(ch[ch["year"] == year]) == expected


@pytest.mark.parametrize("year", YEARS)
def test_reconstructed_seats_fall_below_admits(ch: pd.DataFrame, year: int) -> None:
    """The reason no headline number may rest on `รับ`.

    The best available quota reconstruction is smaller than the number of
    students actually admitted, in every single year. The file is not
    self-consistent on seats, so `passed` is the denominator.
    """
    c = ch[ch["year"] == year]
    assert reconstructed_seats(c) < c["passed"].sum()


def test_groupby_on_major_silently_drops_blank_keys(ch: pd.DataFrame) -> None:
    """Why the loader fills NaN with "" instead of leaving it.

    ~50 Chula rows a year have a blank สาขา/วิชาเอก. pandas' groupby drops NaN
    keys by default, so grouping on the raw column would discard them --
    2,838 of TCAS69's 7,639 seats -- without a warning.
    """
    c69 = ch[ch["year"] == 69].copy()
    assert (c69["major"] == "").sum() == 55

    as_na = c69.assign(major=c69["major"].replace("", np.nan))
    kept = as_na.groupby(["code", "major"], dropna=True)["seats"].sum().sum()
    assert kept < c69["seats"].sum()
    assert c69.loc[c69["major"] == "", "seats"].sum() == 2_838


# --------------------------------------------------------------------------
# Trap 2 — min_score == 0
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("year", "n_zero"), [(66, 12), (67, 10), (68, 16), (69, 19)]
)
def test_chula_zero_min_implies_no_admits(
    ch: pd.DataFrame, year: int, n_zero: int
) -> None:
    """At Chula the rule is clean: a zero floor means nobody was admitted."""
    c = ch[ch["year"] == year]
    zero = c[c["min_score"] == 0]
    assert len(zero) == n_zero
    assert (zero["passed"] == 0).all()


@pytest.mark.parametrize(
    ("year", "n_rows"), [(66, 200), (67, 200), (68, 210), (69, 161)]
)
def test_national_zero_min_with_real_admits_persists(
    df: pd.DataFrame, year: int, n_rows: int
) -> None:
    """The counter-example that must survive any "fix" to Trap 2.

    Nationally, a zero floor alongside real admits is legitimate data --
    private and Rajabhat universities whose Admission criteria are not
    exam-scored. Filtering on `min_score > 0` for validity would delete them.
    """
    y = df[df["year"] == year]
    assert ((y["min_score"] == 0) & (y["passed"] > 0)).sum() == n_rows


def test_zero_min_with_admits_are_not_chula(df: pd.DataFrame) -> None:
    offenders = df[(df["min_score"] == 0) & (df["passed"] > 0)]
    assert CHULA not in set(offenders["univ"])


def test_tcas66_internal_inconsistency_is_66_only(df: pd.DataFrame) -> None:
    """46 national rows in 66 report no admits beside a nonzero floor.

    67-69 have none. This is a defect in the 66 file, not a pattern; the
    project's rule is to leave the rows in place and exclude them via
    `passed > 0` like any other unfilled program.
    """
    counts = {
        year: int(
            (
                (df[df["year"] == year]["passed"] == 0)
                & (df[df["year"] == year]["min_score"] != 0)
            ).sum()
        )
        for year in YEARS
    }
    assert counts == {66: 46, 67: 0, 68: 0, 69: 0}


def test_national_median_sensitive_to_filter_in_level_not_shape(
    df: pd.DataFrame,
) -> None:
    """Both filter variants must be reported: ~1 point apart, same shape."""
    lenient = df[df["passed"] > 0].groupby("year")["min_score"].median().round(2)
    strict = (
        df[(df["passed"] > 0) & (df["min_score"] > 0)]
        .groupby("year")["min_score"]
        .median()
        .round(2)
    )
    assert lenient.to_dict() == {66: 50.64, 67: 51.75, 68: 53.85, 69: 52.66}
    assert strict.to_dict() == {66: 51.71, 67: 52.64, 68: 54.70, 69: 53.33}
    # Same direction year to year, ~1 point of level difference.
    assert np.sign(lenient.diff().dropna()).equals(np.sign(strict.diff().dropna()))
    assert ((strict - lenient).abs() < 1.2).all()


def test_chula_filters_coincide(ch: pd.DataFrame) -> None:
    """At Chula `passed > 0` and `passed > 0 & min > 0` select the same rows.

    A direct consequence of Trap 2's Chula rule, and the reason every Chula
    figure in the spec is "stable under both filters".
    """
    lenient = ch[ch["passed"] > 0]
    strict = ch[(ch["passed"] > 0) & (ch["min_score"] > 0)]
    assert len(lenient) == len(strict)


# --------------------------------------------------------------------------
# Trap 3 — raw vs T-Score universities
# --------------------------------------------------------------------------

def test_tscore_universities_present_and_chula_is_not_one(df: pd.DataFrame) -> None:
    from src.load import TSCORE_UNIVERSITIES

    present = set(df["univ"])
    assert TSCORE_UNIVERSITIES <= present
    assert CHULA not in TSCORE_UNIVERSITIES


# --------------------------------------------------------------------------
# Panel + sanity targets
# --------------------------------------------------------------------------

def test_stable_chula_panel_is_48_codes(df: pd.DataFrame) -> None:
    assert len(stable_chula_codes(df)) == 48


def test_all_66_codes_survive_to_69(df: pd.DataFrame) -> None:
    ch = chula(df)
    codes = {y: set(g["code"]) for y, g in ch.groupby("year")}
    assert codes[66] <= codes[69]
    assert len(codes[69] - codes[66]) == 2


def test_panel_is_balanced_and_scored(df: pd.DataFrame) -> None:
    from src.load import chula_panel

    panel = chula_panel(df)
    assert len(panel) == 48 * 4
    assert not panel["min_score"].isna().any()
    # Score aggregates exclude no-admit rows, so no program floor is a fake 0.
    assert (panel["min_score"] > 0).all()
    assert "seats" not in panel.columns, "seats must not enter the panel (Trap 1)"


def test_chula_faculty_names_identical_across_years(df: pd.DataFrame) -> None:
    """Asserted, not crosswalked — see R2."""
    ch = chula(df)
    sets = {y: frozenset(g["faculty"]) for y, g in ch.groupby("year")}
    assert len(set(sets.values())) == 1
    assert len(sets[66]) == 14


def test_chula_applications_and_admits(ch: pd.DataFrame) -> None:
    """The headline: applications fell 37%, admits did not move."""
    g = ch.groupby("year").agg(applied=("applied", "sum"), passed=("passed", "sum"))
    assert g["applied"].to_dict() == {66: 76_905, 67: 66_806, 68: 54_045, 69: 48_615}
    assert g["passed"].to_dict() == {66: 4_118, 67: 3_916, 68: 4_007, 69: 3_989}
    assert round(1 - g.loc[69, "applied"] / g.loc[66, "applied"], 2) == 0.37


def test_applications_per_admit(ch: pd.DataFrame) -> None:
    g = ch.groupby("year").agg(applied=("applied", "sum"), passed=("passed", "sum"))
    per_admit = (g["applied"] / g["passed"]).round(1)
    assert per_admit.to_dict() == {66: 18.7, 67: 17.1, 68: 13.5, 69: 12.2}


@pytest.mark.parametrize(
    ("faculty", "delta"),
    [
        ("คณะวิทยาศาสตร์", -14.58),
        ("คณะนิเทศศาสตร์", -8.17),
        ("คณะพาณิชยศาสตร์และการบัญชี", -5.31),
        ("คณะครุศาสตร์", 4.72),
        ("คณะรัฐศาสตร์", 3.74),
    ],
)
def test_faculty_median_moves_66_to_69(
    ch: pd.DataFrame, faculty: str, delta: float
) -> None:
    """Filter: `passed > 0`. Stable under `passed > 0 & min > 0` — see
    ``test_chula_filters_coincide`` for why that is automatic at Chula."""
    valid = ch[ch["passed"] > 0]
    med = valid[valid["faculty"] == faculty].groupby("year")["min_score"].median()
    assert round(med[69] - med[66], 2) == delta


def test_headline_tension_holds(ch: pd.DataFrame) -> None:
    """Far fewer applications, and the bar did not fall. The project's thesis."""
    valid = ch[ch["passed"] > 0]
    med = valid.groupby("year")["min_score"].median()
    apps = ch.groupby("year")["applied"].sum()
    assert apps[69] < 0.65 * apps[66]
    assert med[69] >= med[66]


def test_outlier_faculties_are_undersubscribed_not_unfilled(ch: pd.DataFrame) -> None:
    """วิทยาศาสตร์การกีฬา +27.1 and ทรัพยากรการเกษตร +25.9 — the real mechanism.

    The spec calls these "artefacts of near-unfilled 66 programs". That is not
    what the data shows: both filled their seats in TCAS66 (40 admits, and
    10/10/8/34). What was anomalous is *demand*. They drew 1.8 and 3.7
    applications per admit against a Chula-wide 18.7, so their floor sat far
    below the university's, and it normalised once applications arrived
    (วิทยาศาสตร์การกีฬา: 72 applications in 66 -> 635 in 67).

    So the +27 move is a real competition change off an undersubscribed base,
    not a data artefact — but it measures something different from the other
    faculties and should be reported with the base rate attached, not dropped.
    """
    chula_66 = ch[ch["year"] == 66]
    baseline = chula_66["applied"].sum() / chula_66["passed"].sum()
    assert round(baseline, 1) == 18.7

    for faculty, expected in (
        ("คณะวิทยาศาสตร์การกีฬา", 1.8),
        ("สำนักวิชาทรัพยากรการเกษตร", 3.7),
    ):
        f66 = chula_66[chula_66["faculty"] == faculty]
        assert (f66["passed"] > 0).all(), "these programs filled — not unfilled"
        ratio = f66["applied"].sum() / f66["passed"].sum()
        assert round(ratio, 1) == expected
        assert ratio < baseline / 4


# --------------------------------------------------------------------------
# Double Sorting
# --------------------------------------------------------------------------

def test_ds_usually_lowers_the_floor_but_not_always(df: pd.DataFrame) -> None:
    """The spec claims `min_ds <= min` in every row. It is not true.

    Nationally 333/337/352 rows in 67/68/69 have a *higher* DS floor, and 3/3/1
    of those are Chula. The mechanism is real: when marginal admits decline
    their seat, the remaining floor can rise. Two TCAS68 Chula rows go from
    `passed == 0` to a real DS admit, which necessarily raises the floor
    from 0. So the DS section must not assume a one-way move.
    """
    both = df.dropna(subset=["min_score", "min_score_ds"])
    higher = both[both["min_score_ds"] > both["min_score"] + 1e-9]
    assert not higher.empty
    per_year = higher.groupby("year").size().to_dict()
    assert per_year == {67: 333, 68: 337, 69: 352}
    # Still overwhelmingly a downward move.
    assert (both["min_score_ds"] <= both["min_score"] + 1e-9).mean() > 0.90


def test_ds_columns_exist_only_for_67_69(df: pd.DataFrame) -> None:
    has_ds = df.dropna(subset=["min_score_ds"]).groupby("year").size()
    assert set(has_ds.index) == {67, 68, 69}


# --------------------------------------------------------------------------
# Exam-scale transcription (R3's strongest validation, kept as a test)
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def exam_stats() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "exam_subject_stats.csv")


@pytest.fixture(scope="module")
def coefficients() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "tscore_coefficients.csv")


def test_tscore_coefficient_identity(
    exam_stats: pd.DataFrame, coefficients: pd.DataFrame
) -> None:
    """`c == 50 / max|z|`, where max runs over every subject in that family-year.

    The scale is pinned by the single most extreme individual score in the
    whole cohort. This reproduces all 8 published coefficients and is the
    strongest available check that the transcription is correct.
    """
    assert len(coefficients) == 8
    for _, row in coefficients.iterrows():
        g = exam_stats[
            (exam_stats["exam_family"] == row["exam_family"])
            & (exam_stats["tcas_year"] == row["tcas_year"])
        ]
        z_lo = (g["mean"] - g["min"]) / g["sd"]
        z_hi = (g["max"] - g["mean"]) / g["sd"]
        implied = 50.0 / np.maximum(z_lo, z_hi).max()
        rel_err = abs(implied - row["tscore_coefficient"]) / row["tscore_coefficient"]
        assert rel_err < 5e-4, (
            f"{row['exam_family']} {row['tcas_year']}: "
            f"implied {implied:.5f} vs published {row['tscore_coefficient']:.5f} "
            f"({rel_err:.4%})"
        )


def test_tgat_tpat_scale_driven_by_tpat5_minimum(exam_stats: pd.DataFrame) -> None:
    """In every year one candidate's TPAT5 score sets the scale for everyone."""
    for year in YEARS:
        g = exam_stats[
            (exam_stats["exam_family"] == "TGAT/TPAT")
            & (exam_stats["tcas_year"] == year)
        ].copy()
        g["z_lo"] = (g["mean"] - g["min"]) / g["sd"]
        g["z_hi"] = (g["max"] - g["mean"]) / g["sd"]
        g["zmax"] = g[["z_lo", "z_hi"]].max(axis=1)
        driver = g.loc[g["zmax"].idxmax()]
        assert driver["subject_en"] == "TPAT5"
        assert driver["z_lo"] > driver["z_hi"], "driven by the minimum, not the maximum"


def test_exam_stats_shape(exam_stats: pd.DataFrame) -> None:
    assert len(exam_stats) == 108
    counts = exam_stats.groupby(["exam_family", "tcas_year"]).size().unstack()
    assert (counts.loc["A-Level"] == 16).all()
    assert (counts.loc["TGAT/TPAT"] == 11).all()
