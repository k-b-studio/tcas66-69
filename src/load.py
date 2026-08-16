"""Tidy loader for the four TCAS รอบ 3 min/max score files (R1).

One dict — ``YEAR_COLUMNS`` — holds every year-specific column name. Nothing
else in the codebase should know that the files disagree about spelling.

The headline series is **first-processing** (ประมวลผลครั้งที่ 1) only. The
second-pass columns are all the same mechanism (Double Sorting) under three
different names, and are carried separately as ``*_ds`` so they can never be
mixed into the main series. See ``specs/`` Trap notes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data"
PROCESSED = REPO / "data" / "processed"

CHULA = "จุฬาลงกรณ์มหาวิทยาลัย"
YEARS = (66, 67, 68, 69)

#: Canonical tidy schema, in order.
SCHEMA = [
    "year", "univ", "campus", "code", "faculty", "program", "detail", "major",
    "seats", "applied", "passed", "min_score", "max_score",
    "min_score_ds", "max_score_ds", "passed_ds",
]

#: Every year-specific column name lives here and nowhere else.
#: ``None`` means the year does not publish that column (TCAS66 has no
#: second pass — ทปอ. ran Double Sorting but never published it).
YEAR_COLUMNS: dict[int, dict[str, str | None]] = {
    66: {
        "sheet": "maxmin66",
        "univ": "สถาบัน", "campus": "วิทยาเขต", "code": "รหัสหลักสูตร",
        "faculty": "คณะ/สำนักวิชา", "program": "ชื่อหลักสูตร",
        "detail": "รายละเอียด", "major": "สาขาวิชา/วิชาเอก",
        "seats": "รับ", "applied": "สมัคร", "passed": "ผ่าน",
        "min_score": "คะแนนต่ำสุด", "max_score": "คะแนนสูงสุด",
        "min_score_ds": None, "max_score_ds": None, "passed_ds": None,
    },
    67: {
        "sheet": "Sheet2",
        "univ": "สถาบัน", "campus": "วิทยาเขต", "code": "รหัสหลักสูตร",
        "faculty": "คณะ", "program": "หลักสูตร",
        "detail": "รายละเอียด", "major": "สาขา/วิชาเอก",
        "seats": "รับ", "applied": "สมัคร", "passed": "ผ่าน(รอบ1)",
        "min_score": "คะแนนต่ำสุด", "max_score": "คะแนนสูงสุด",
        "min_score_ds": "คะแนนต่ำสุด หลังประมวลผลรอบ 2",
        "max_score_ds": "คะแนนสูงสุด หลังประมวลผลรอบ 2",
        "passed_ds": "ผ่าน(รอบ2)",
    },
    68: {
        "sheet": "Sheet1",
        "univ": "สถาบัน", "campus": "วิทยาเขต", "code": "รหัสหลักสูตร",
        "faculty": "คณะ", "program": "หลักสูตร",
        "detail": "รายละเอียด", "major": "สาขา/วิชาเอก",
        "seats": "รับ", "applied": "สมัคร",
        "passed": "ผ่าน ประมวลผลครั้งที่ 1",
        "min_score": "คะแนนต่ำสุด ประมวลผลครั้งที่ 1",
        "max_score": "คะแนนสูงสุด ประมวลผลครั้งที่ 1",
        "min_score_ds": "คะแนนต่ำสุด ประมวลผลครั้งที่ 2",
        "max_score_ds": "คะแนนสูงสุด ประมวลผลครั้งที่ 2",
        "passed_ds": "ผ่าน ประมวลผลครั้งที่ 2",
    },
    69: {
        "sheet": "Sheet1",
        "univ": "สถาบัน", "campus": "วิทยาเขต", "code": "รหัสหลักสูตร",
        "faculty": "คณะ", "program": "หลักสูตร",
        "detail": "รายละเอียด", "major": "สาขา/วิชาเอก",
        "seats": "รับ", "applied": "สมัคร", "passed": "ผ่าน",
        "min_score": "คะแนนต่ำสุด", "max_score": "คะแนนสูงสุด",
        "min_score_ds": "คะแนนต่ำสุด DS", "max_score_ds": "คะแนนสูงสุด DS",
        "passed_ds": "ผ่าน DS",
    },
}

#: Regression guards — if the loader changes, these move.
EXPECTED_ROWS = {66: 4670, 67: 4718, 68: 4945, 69: 5104}
EXPECTED_NATIONAL_KEY_COLLISIONS = {66: 27, 67: 34, 68: 32, 69: 2}

#: The row grain. Unique within Chula in all four years; collides nationally.
ROW_KEY = ["code", "detail", "major"]

#: Universities whose published composite is T-Score-weighted, not raw-percent
#: (Trap 3). Cross-university score comparisons involving these are
#: apples-to-oranges and must be marked in any chart.
TSCORE_UNIVERSITIES = {
    "สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง",
    "มหาวิทยาลัยเชียงใหม่",
    "มหาวิทยาลัยธรรมศาสตร์",
    "มหาวิทยาลัยศิลปากร",
    "มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี",
}

_STRING_COLS = ["univ", "campus", "code", "faculty", "program", "detail", "major"]
_NUMERIC_COLS = [
    "seats", "applied", "passed", "min_score", "max_score",
    "min_score_ds", "max_score_ds", "passed_ds",
]


def load_year(year: int, path: Path | None = None) -> pd.DataFrame:
    """Read one TCAS xlsx into the canonical schema."""
    spec = YEAR_COLUMNS[year]
    path = path or RAW / f"TCAS{year}_maxmin.xlsx"
    raw = pd.read_excel(path, sheet_name=spec["sheet"])

    missing = [
        src for key, src in spec.items()
        if key != "sheet" and src is not None and src not in raw.columns
    ]
    if missing:
        raise KeyError(f"TCAS{year}: mapped columns absent from file: {missing}")

    out = pd.DataFrame(index=raw.index)
    out["year"] = year
    for key in SCHEMA[1:]:
        src = spec[key]
        out[key] = pd.NA if src is None else raw[src]

    # Positional id, assigned before any filtering, so the 27/34/32/2 national
    # key collisions can be logged and kept rather than dropped.
    out["row_id"] = range(len(out))

    for col in _STRING_COLS:
        # NaN -> "" is not cosmetic. `รายละเอียด` and `สาขา/วิชาเอก` are empty
        # on ~50 Chula rows a year, and pandas' groupby drops NaN keys by
        # default -- grouping on them silently discards those rows (2,838 of
        # 7,639 TCAS69 Chula seats). An empty string groups instead of vanishing.
        out[col] = out[col].astype("string").fillna("").str.strip()

    for col in _NUMERIC_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out[["year", *SCHEMA[1:], "row_id"]]


def load_all(years: tuple[int, ...] = YEARS) -> pd.DataFrame:
    """Concatenate every year into one tidy frame."""
    return pd.concat([load_year(y) for y in years], ignore_index=True)


def chula(df: pd.DataFrame) -> pd.DataFrame:
    """Rows for Chulalongkorn only.

    Exact equality, never ``contains("จุฬา")`` -- that also matches
    มหาวิทยาลัยมหาจุฬาลงกรณราชวิทยาลัย and ราชวิทยาลัยจุฬาภรณ์, which inflates
    TCAS69 applications from 48,615 to 49,976.
    """
    return df[df["univ"] == CHULA]


def reconstructed_seats(df: pd.DataFrame) -> float:
    """The **only** sanctioned way to aggregate ``seats``. Read this first.

    ``รับ`` cannot be summed. One ``code`` explodes into many rows -- one per
    (สาขา x เลือกสอบวิชา) combination -- each repeating a shared quota, so a raw
    sum roughly doubles the true figure (Chula TCAS69: 7,639).

    This applies the best available rule: drop duplicate (code, major, seats)
    triples, then sum. It is still **not correct**. The result comes out *below*
    the number of students actually admitted in all four years:

        year    reconstructed    admits
        66             4,036     4,118
        67             3,837     3,916
        68             3,815     4,007
        69             3,847     3,989

    So the published file does not permit an exact seat count, and no headline
    number should rest on it. A true seat count has to come from each faculty's
    own ประกาศ. Use ``passed`` (admits) as the denominator instead.
    """
    return df.drop_duplicates(subset=["code", "major", "seats"])["seats"].sum()


def validate(df: pd.DataFrame) -> dict[str, object]:
    """Assert the invariants that everything downstream depends on.

    Raises ``AssertionError`` on any breach. Returns a report of the things
    that are logged rather than asserted.
    """
    report: dict[str, object] = {}

    for year in sorted(df["year"].unique()):
        year_df = df[df["year"] == year]
        n = len(year_df)
        assert n == EXPECTED_ROWS[year], (
            f"TCAS{year}: {n} rows, expected {EXPECTED_ROWS[year]}"
        )

        ch = chula(year_df)

        # Grain: unique within Chula. Asserted here, only logged nationally.
        dupes = ch.duplicated(subset=ROW_KEY).sum()
        assert dupes == 0, f"TCAS{year}: {dupes} duplicate Chula row keys"

        # min <= max. Hard assert for Chula; logged nationally, because the
        # source files contain at least one genuine ทปอ. error: TCAS67
        # ราชวิทยาลัยจุฬาภรณ์ 10320104112101A publishes min=46.3295, max=10.0,
        # while its own DS columns read min=40.8607, max=46.3295. The real max
        # is 46.3295. It is left uncorrected and visible rather than patched.
        both = year_df.dropna(subset=["min_score", "max_score"])
        inverted = both[both["min_score"] > both["max_score"]]
        ch_inverted = inverted[inverted["univ"] == CHULA]
        assert ch_inverted.empty, (
            f"TCAS{year}: {len(ch_inverted)} Chula rows with min_score > max_score"
        )
        report[f"national_min_gt_max_{year}"] = int(len(inverted))

        # Trap 2: at Chula, a zero floor means nobody was admitted. This is a
        # Chula-only rule -- it is emphatically false nationally.
        zero = ch[ch["min_score"] == 0]
        assert (zero["passed"] == 0).all(), (
            f"TCAS{year}: Chula rows with min_score == 0 but passed > 0"
        )

        national_dupes = int(year_df.duplicated(subset=ROW_KEY).sum())
        report[f"national_key_collisions_{year}"] = national_dupes

        # Trap 2's counter-example, kept visible so nobody "fixes" it.
        counter = int(((year_df["min_score"] == 0) & (year_df["passed"] > 0)).sum())
        report[f"national_zero_min_with_admits_{year}"] = counter

        # TCAS66-only internal inconsistency, nationally: 46 rows report no
        # admits alongside a nonzero floor. 67-69 have none.
        inconsistent = int(((year_df["passed"] == 0) & (year_df["min_score"] != 0)).sum())
        report[f"national_no_admits_nonzero_min_{year}"] = inconsistent

    # Faculty names are byte-identical across all four years, so the panel needs
    # no crosswalk. Assert it; if this ever fires, build one.
    faculty_sets = {
        year: frozenset(chula(df[df["year"] == year])["faculty"])
        for year in sorted(df["year"].unique())
    }
    assert len(set(faculty_sets.values())) == 1, (
        "Chula faculty names are no longer identical across years -- a "
        f"crosswalk is now required. Sets: {faculty_sets}"
    )
    report["chula_faculties"] = sorted(next(iter(faculty_sets.values())))

    return report


def stable_chula_codes(df: pd.DataFrame) -> list[str]:
    """Program codes present at Chula in every year — the balanced panel (48)."""
    ch = chula(df)
    per_year = [set(g["code"]) for _, g in ch.groupby("year")]
    return sorted(set.intersection(*per_year))


def chula_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Balanced (code x year) panel over the 48 stable Chula codes — R2.

    One published code fans out into several rows, one per
    (สาขา x เลือกสอบวิชา) variant, so the panel has to aggregate. The rules:

    * ``applied`` / ``passed`` are summed — both are genuinely per-row.
    * Score aggregates use **only rows with ``passed > 0``**. A row with no
      admits carries ``min_score == 0`` at Chula (Trap 2), and including it
      would drag the floor to zero.
    * ``min_score`` is the *lowest* floor across variants — the program's true
      entry point. ``min_score_median`` is carried alongside because the min is
      sensitive to a single thin variant; the model can pick.
    * ``seats`` is deliberately absent (Trap 1).
    """
    ch = chula(df)
    ch = ch[ch["code"].isin(stable_chula_codes(df))]
    scored = ch[ch["passed"] > 0]

    volume = ch.groupby(["code", "year"]).agg(
        faculty=("faculty", "first"),
        program=("program", "first"),
        n_rows=("code", "size"),
        applied=("applied", "sum"),
        passed=("passed", "sum"),
    )
    scores = scored.groupby(["code", "year"]).agg(
        min_score=("min_score", "min"),
        min_score_median=("min_score", "median"),
        max_score=("max_score", "max"),
        n_scored_rows=("code", "size"),
    )
    panel = volume.join(scores, how="left").reset_index()
    panel["apps_per_admit"] = panel["applied"] / panel["passed"].replace(0, pd.NA)

    n_codes, n_years = panel["code"].nunique(), panel["year"].nunique()
    assert len(panel) == n_codes * n_years, "panel is not balanced"
    return panel.sort_values(["faculty", "code", "year"], ignore_index=True)


def write(df: pd.DataFrame, outdir: Path = PROCESSED) -> tuple[Path, Path]:
    """Persist the tidy frame as parquet (canonical) + csv (for eyeballing)."""
    outdir.mkdir(parents=True, exist_ok=True)
    pq, csv = outdir / "admission_long.parquet", outdir / "admission_long.csv"
    df.to_parquet(pq, index=False)
    df.to_csv(csv, index=False)
    return pq, csv


if __name__ == "__main__":
    frame = load_all()
    info = validate(frame)
    paths = write(frame)
    print(f"loaded {len(frame):,} rows over {frame['year'].nunique()} years")
    print(f"stable Chula codes: {len(stable_chula_codes(frame))}")
    for key, value in info.items():
        if key != "chula_faculties":
            print(f"  {key}: {value}")
    print(f"wrote {paths[0].name}, {paths[1].name}")
