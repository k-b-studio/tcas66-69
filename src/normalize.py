"""Exam-scale normalization (R3) — the defence against exam drift.

A raw-weighted composite inherits every year-to-year wobble in paper
difficulty: A-Level เคมี's mean went 18.40 -> 19.11 -> 25.22 -> 22.49, and
ฟิสิกส์'s SD went 10.91 -> 13.86 -> 12.37 -> 9.67. A program's min score can
move several points without its competitiveness changing at all.

Two scale-free tracks are provided:

* :func:`national_percentile_rank` — where a program sits inside its own
  year's national distribution. Immune to any monotone rescaling of the
  composite, so it is the primary comparison across years.
* :func:`cohort_difficulty_index` — how hard the papers were that year, so a
  chart can show "the papers moved" beside "the bar moved".
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.load import PROCESSED

#: Composite subjects that are aggregates of their own parts. Counting both
#: the whole and the parts would double-weight those candidates.
_COMPOSITE_SUBJECTS = {"TGAT", "TPAT2"}


def load_exam_stats() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "exam_subject_stats.csv")


def load_coefficients() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "tscore_coefficients.csv")


def national_percentile_rank(df: pd.DataFrame) -> pd.Series:
    """Percentile of each row's ``min_score`` within its own year, nationally.

    The reference distribution is every valid row that year — ``passed > 0``,
    never ``min_score > 0`` (Trap 2). Returns NaN for invalid rows.

    Because the rank is taken *within* a year, it is unaffected by any monotone
    change to the composite scale. That is the whole point: it answers "did
    this program get harder relative to everything else in Thailand" rather
    than "did the number go up".
    """
    valid = df["passed"] > 0
    out = pd.Series(np.nan, index=df.index, dtype="float64")
    for year, group in df[valid].groupby("year"):
        out.loc[group.index] = group["min_score"].rank(pct=True) * 100.0
    return out


def with_percentile_rank(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(pct_rank=national_percentile_rank(df))


def cohort_difficulty_index(exam_stats: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per (family, year): how hard the papers were.

    ``mean_index`` is the examinee-weighted mean of subject means — a big
    subject like TGAT should dominate a niche language paper. ``sd_index`` is
    the examinee-weighted mean SD, i.e. how spread out the cohort was.

    Composite subjects (TGAT, TPAT2) are dropped so their sub-parts are not
    counted twice.
    """
    stats = exam_stats if exam_stats is not None else load_exam_stats()
    parts = stats[~stats["subject_en"].isin(_COMPOSITE_SUBJECTS)]

    def _weighted(group: pd.DataFrame) -> pd.Series:
        w = group["n_examinees"]
        return pd.Series({
            "mean_index": np.average(group["mean"], weights=w),
            "sd_index": np.average(group["sd"], weights=w),
            "n_subjects": len(group),
            "n_examinees": w.sum(),
        })

    return (
        parts.groupby(["exam_family", "tcas_year"])[
            ["mean", "sd", "n_examinees"]
        ]
        .apply(lambda g: _weighted(g))
        .reset_index()
    )


def tscore_drivers(
    exam_stats: pd.DataFrame | None = None,
    coefficients: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Which single subject pinned each year's T-Score scale, and how well.

    ``c == 50 / max|z|`` where the max runs over every subject in the family
    that year — so the scale is set by the most extreme individual score in
    the whole cohort. Returns the driving subject, the side it came from, the
    implied coefficient and the relative error against the published one.
    """
    stats = exam_stats if exam_stats is not None else load_exam_stats()
    coeffs = coefficients if coefficients is not None else load_coefficients()

    rows = []
    for _, row in coeffs.iterrows():
        g = stats[
            (stats["exam_family"] == row["exam_family"])
            & (stats["tcas_year"] == row["tcas_year"])
        ].copy()
        g["z_lo"] = (g["mean"] - g["min"]) / g["sd"]
        g["z_hi"] = (g["max"] - g["mean"]) / g["sd"]
        g["zmax"] = g[["z_lo", "z_hi"]].max(axis=1)
        top = g.loc[g["zmax"].idxmax()]
        implied = 50.0 / top["zmax"]
        from_min = top["z_lo"] >= top["z_hi"]
        rows.append({
            "exam_family": row["exam_family"],
            "tcas_year": row["tcas_year"],
            "published_c": row["tscore_coefficient"],
            "implied_c": implied,
            "rel_error": abs(implied - row["tscore_coefficient"]) / row["tscore_coefficient"],
            "driver": top["subject_en"],
            "driver_th": top["subject_th"],
            "side": "min" if from_min else "max",
            "driver_value": top["min"] if from_min else top["max"],
        })
    return pd.DataFrame(rows)
