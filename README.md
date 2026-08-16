# TCAS รอบ 3 Admission — TCAS66–69

Four years of ทปอ. รอบ 3 Admission min/max score files (TCAS66–69), turned into a
tidy panel, a set of figures, and a forecast — with a Chulalongkorn focus.

The question: **how much harder has it become to get into Chula, faculty by
faculty?** Answering it honestly means separating three things a naive min-score
time series silently mixes together:

1. **Real competition change** — more applicants chasing the same seats.
2. **Exam-scale drift** — the same ability produces a different score each year.
3. **File-format drift** — ทปอ. changed the published column set all four years.

Full brief: [`specs/tcas-admission-trend-analysis.md`](specs/tcas-admission-trend-analysis.md).
Written answer: [`reports/findings.md`](reports/findings.md).

---

## What the data says

| | 66 | 67 | 68 | 69 |
|---|---|---|---|---|
| applications (`สมัคร`) | 76,905 | 66,806 | 54,045 | 48,615 |
| admits (`ผ่าน`) | 4,118 | 3,916 | 4,007 | 3,989 |
| **applications per admit** | **18.7** | **17.1** | **13.5** | **12.2** |
| median min score (`passed>0`) | 64.43 | 63.66 | 69.34 | 66.88 |
| median percentile rank | 77.8 | 75.9 | 81.1 | 78.0 |

- **Applications to Chula fell 37% and the bar did not fall.** Competition per
  admitted student dropped by a third; the floor went *up* 2.4 raw points and did
  not move at all on percentile rank.
- **It is not demographics.** On a like-for-like panel the rest of the sector lost
  4% of its applications while Chula lost 37%; KMITL, Mahidol, KMUTT and Silpakorn
  *gained* 25–60%. Demand moved, it did not evaporate.
- **Raw scores flatter Chula.** Ranked inside each year's national distribution,
  every faculty looks worse than its raw points suggest, and two (จิตวิทยา,
  นิติศาสตร์) flip sign. คณะวิทยาศาสตร์ falls from the 70th percentile to the
  34th — all 17 of its 17 programs down.
- **The T-Score coefficient `c` is exactly `50 / max|z|`** — pinned by the single
  most extreme individual score in the cohort. Reproduces all 8 published
  coefficients to within 0.017%. A T-Score 60 is not the same achievement in 66
  and 69, so every T-Score university has a scale break at each year boundary.
- **The forecast loses to a trivial baseline, and says so.** With n = 4 per
  program, last-value-carried-forward beats the partially-pooled hierarchical
  model, so LVCF ships with an 80% interval ~17 points wide.

---

## Layout

```
data/
  TCAS{66,67,68,69}_maxmin.xlsx    source files, 4,670 / 4,718 / 4,945 / 5,104 rows
  alevel/, tgat-tpat/              ทปอ. published exam stat sheets (jpg + one xlsx)
  processed/
    exam_subject_stats.csv         INPUT  — 108 rows, transcribed + verified
    tscore_coefficients.csv        INPUT  — 8 rows, published T-Score coefficients
    admission_long.{parquet,csv}   OUTPUT — 19,437 tidy rows, one schema
    chula_panel.csv                OUTPUT — balanced 48-code × 4-year panel
    forecast_tcas70.csv            OUTPUT — 48 programs, point + 80%/95% intervals
src/
  load.py                          year column mapping, tidy loader, assertions
  normalize.py                     percentile rank, cohort difficulty, T-Score check
  viz.py                           Thai font resolution, palette, all eight figures
  model.py                         baselines, hierarchical model, backtest, forecast
  build_exam_stats.py              transcription source for the two input CSVs
  verify_exam_stats.py             standalone checks on that transcription
nb/
  01_clean.ipynb                   load → assert → write; the three traps with numbers
  04_visualize.ipynb               all eight figures
  05_model.ipynb                   baselines → model → validation → forecast
  tcas-data-clean.ipynb            original scratch notebook, superseded by 01
tests/                             93 tests — traps, sanity targets, model, Thai glyphs
reports/
  findings.md                      the written answer
  findings.html                    same, as a standalone page with figures embedded
  figures/*.png                    eight figures, Thai text verified
```

`data/processed/exam_subject_stats.csv` and `tscore_coefficients.csv` are **inputs,
not outputs** — transcribed from the images and verified (see the Provenance
section of the spec). Do not re-OCR them.

---

## Running it

Python 3.11+ (developed on 3.13). No virtualenv is checked in.

```bash
pip install pandas numpy pyarrow openpyxl matplotlib statsmodels scipy

python -m src.load       # → admission_long.{parquet,csv}, prints the validation report
python -m src.model      # → forecast_tcas70.csv, prints the backtest table
python -m pytest         # 93 tests, ~20s
```

Notebooks run top-to-bottom from a clean kernel and import from `src/`; run them
from the repo root so `src` is importable.

**Thai fonts.** matplotlib will silently fall back to DejaVu Sans and draw a box
per Thai glyph. `viz.setup()` refuses to trust a font by name — it reads the font
file's own charmap, then does a live render and fails on matplotlib's
missing-glyph warning. If no Thai font is found it raises with an install hint
(`brew install --cask font-sarabun`).

---

## Three traps that silently corrupt results

Each one is demonstrated numerically in `nb/01_clean.ipynb` and locked in
`tests/test_traps.py`.

**1. `รับ` (seats) cannot be summed.** One `รหัสหลักสูตร` fans out into many rows,
one per (สาขา × เลือกสอบวิชา), each repeating a shared quota. Every dedup rule
fails: raw `sum()` gives 7,639 for Chula 69 (≈2× inflated); `groupby(code).first()`
discards a real 209-seat pool; the best reconstruction (3,847) comes out *below*
the 3,989 students actually admitted. **Use `ผ่าน` (admits) as the denominator.**
`src.load.reconstructed_seats()` is the only sanctioned way to touch the column,
and its docstring explains why the answer is still wrong.

**2. `min_score == 0` means "nobody admitted" at Chula — but not nationally.**
At Chula it coincides with `passed == 0` in 100% of cases. Nationally, 161–210 rows
a year have a genuine zero floor beside real admits (private and Rajabhat
universities whose criteria are not exam-scored). **Filter on `passed > 0`, never
on `min_score > 0`.** The national median shifts ~1 point between the two filters;
the shape is identical, so conclusions about direction are safe and conclusions
about level are not.

**3. Most universities score in raw percent, a few in T-Score.** KMITL, Chiang Mai,
Thammasat (plus Silpakorn and RMUTT in some years) publish T-Score-weighted
composites. Chula publishes raw. Those series are drawn dashed with square markers
in every chart — compare their *shape* over time, never their *level* against
Chula's.

Two further things the source files get wrong, left visible rather than patched:
TCAS67 ราชวิทยาลัยจุฬาภรณ์ `10320104112101A` publishes `min = 46.33, max = 10.0`,
and TCAS66 has 46 national rows reporting no admits beside a nonzero floor.

---

## Figures

| file | what it shows |
|---|---|
| `01_faculty_raw_vs_normalized.png` | 14 faculty panels on raw score, and the same grid on percentile rank beneath — divergence is exam drift |
| `03_faculty_*.png` | every program inside วิศวกรรมศาสตร์ / อักษรศาสตร์ / รัฐศาสตร์ |
| `04_min_max_spread.png` | max − min per program. Not a clean narrowing: 11.29 → 7.65 → 9.43 → 10.14 |
| `05_competition.png` | applications, admits, applications-per-admit — Chula vs 8 peers. The headline |
| `06_peer_comparison.png` | median min score by university, T-Score scorers marked, with the scale warning |
| `07_exam_difficulty.png` | subject means/SDs by year, the T-Score coefficient, and the subject that pinned it |
| `08_ds_effect.png` | what Double Sorting does to the floor, TCAS67–69 |

Regenerate with `nb/04_visualize.ipynb`.

---

## Status against the spec

Built and green: R1 (loader + assertions), R2 (panel), R3 (normalization), R4
(all eight figures), R5 (model + forecast), R7 (findings). `pytest` covers the
row counts, the national collision counts (27/34/32/2), both sides of the
zero-score rule, the seat-dedup failures, the sanity targets, and the
`c = 50/max|z|` identity.

Deviations, all deliberate:

- **Notebooks 02, 03 and 06 were not written.** Their content lives elsewhere —
  the traps are demonstrated in `nb/01_clean` and locked in `tests/test_traps.py`,
  normalization is in `src/normalize.py` and exercised by `nb/04`, and the findings
  are in `reports/findings.md`. What exists is `01`, `04`, `05`.
- **`statsmodels MixedLM`, not `numpyro`/`pymc`** — neither is installed here, so
  the model uses the spec's sanctioned fallback: random intercept and slope per
  program, faculty as a fixed effect. A two-level approximation to the spec's
  three-level design. Since the model loses to LVCF by a wide margin and the
  *unpooled* variant loses by more, a fuller Bayesian version would have to
  overturn the whole gradient to change the conclusion.
- **Model selection uses a rolling origin, not the single spec holdout.** Every
  method's bias flips sign between 67→68 and 68→69, so one held-out year rewards
  whichever method happened to lean the right way. `program_mean` wins the single
  holdout; `lvcf` wins pooled and is the only method stable at both. The gap was
  never statistically real (paired t p = 0.38, bootstrap CI spanning zero).

Two of the spec's own assumptions turned out false in the data, and are corrected
in the findings: Double Sorting does **not** only lower the floor (it raises it in
~8% of rows), and the min–max spread is **not** steadily narrowing.

The highest-leverage improvement available is not a better model — it is more
data. `assets.mytcas.com/maxmin/TCAS{64,65}_maxmin.xlsx` would take the panel from
4 points to 6. TCAS62–63 predate TGAT/TPAT entirely and do not help.

---

## Scope

รอบ 3 Admission only. Program-level floors only — no individual-applicant odds,
which would need applicant-level data that is not published. Everything needed is
on disk; nothing scrapes mytcas.
