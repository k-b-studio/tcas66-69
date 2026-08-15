# TCAS Admission Trend Analysis (รอบ 3), TCAS66–69 — Chulalongkorn focus

## Goal

Turn four years of TCAS รอบ 3 Admission min/max score files into a defensible picture of how hard it has become to get into Chulalongkorn University, faculty by faculty and major by major — and produce a forecast for TCAS70 that is honest about the fact that each program has only four observations.

The analysis must separate three things that a naive min-score time series silently mixes together:

1. **Real competition change** — more applicants chasing the same seats.
2. **Exam-scale drift** — the same raw ability produces a different subject score each year because the papers differ in difficulty.
3. **File-format drift** — ทปอ. changed the published column set in all four years, and picking the wrong column injects a fake break.

---

## Context the implementer needs (already established — do not re-derive)

### Data on disk

```
data/
  TCAS66_maxmin.xlsx      sheet 'maxmin66'   4,670 rows × 13 cols
  TCAS67_maxmin.xlsx      sheet 'Sheet2'     4,718 rows × 16 cols
  TCAS68_maxmin.xlsx      sheet 'Sheet1'     4,945 rows × 16 cols
  TCAS69_maxmin.xlsx      sheet 'Sheet1'     5,104 rows × 18 cols
  alevel/                 12 jpg stat sheets  (already transcribed)
  tgat-tpat/              1 xlsx + 8 jpg      (already transcribed)
processed/
  exam_subject_stats.csv     108 rows — subject × year basic stats, all 4 years, both exam families
  tscore_coefficients.csv      8 rows — published T-Score coefficient per family × year
nb/
  tcas-data-clean.ipynb   existing scratch notebook — superseded by nb/01_clean.ipynb below
```

`processed/*.csv` were transcribed from the source images and **verified** (see `Provenance` at the end). Treat them as trusted inputs; do not re-OCR the images.

### Column mapping across years — the canonical series

Column names differ every year. The only series comparable across all four years is **first-processing** (ประมวลผลครั้งที่ 1):

| year | faculty col | program col | min score (canonical) | max score (canonical) | passed (canonical) |
|---|---|---|---|---|---|
| 66 | `คณะ/สำนักวิชา` | `ชื่อหลักสูตร` | `คะแนนต่ำสุด` | `คะแนนสูงสุด` | `ผ่าน` |
| 67 | `คณะ` | `หลักสูตร` | `คะแนนต่ำสุด` | `คะแนนสูงสุด` | `ผ่าน(รอบ1)` |
| 68 | `คณะ` | `หลักสูตร` | `คะแนนต่ำสุด ประมวลผลครั้งที่ 1` | `คะแนนสูงสุด ประมวลผลครั้งที่ 1` | `ผ่าน ประมวลผลครั้งที่ 1` |
| 69 | `คณะ` | `หลักสูตร` | `คะแนนต่ำสุด` | `คะแนนสูงสุด` | `ผ่าน` |

Second-pass columns — 67 `หลังประมวลผลรอบ 2`, 68 `ประมวลผลครั้งที่ 2`, 69 `* DS` — are the **same mechanism**: Double Sorting, a re-run of selection after ยืนยันสิทธิ์ frees seats. It only ever lowers the floor (`min_DS ≤ min` in every row; `max_DS == max` almost everywhere). TCAS66 ran Double Sorting too but ทปอ. never published its second pass, so 66 has no second-pass column at all.

**Rule: build the headline series from first-processing only. Carry the second-pass columns as a separate `min_score_ds` field for 67–69 and use them only for a dedicated "what DS does to the floor" section.** Mixing them creates a spurious drop at 66→67.

`รหัสหลักสูตร` is the stable join key: all 48 Chula codes present in 66 are still present in 69 (2 new codes appear in 69). Nationally 2,848 codes appear in all four years.

### Three data traps that will silently corrupt results

**Trap 1 — `รับ` (seats) cannot be summed, and there is no dedup rule that fully fixes it.**
One `รหัสหลักสูตร` explodes into many rows, one per (สาขา × เลือกสอบวิชา) combination — e.g. คณะรัฐศาสตร์ สาขาวิชาการปกครอง has 7 rows for 7 elective-exam variants, all repeating one shared quota. Naive `sum(รับ)` over Chula 69 rows gives 7,639.

But every candidate dedup rule fails, and this was checked empirically:

| rule | Chula 69 seats | verdict |
|---|---|---|
| `sum()` raw | 7,639 | inflated ~2× by repeated quotas |
| `groupby(code).first()` | 2,728 | **wrong** — code `10010122904301A` (อักษรศาสตร์) holds two distinct pools, 20 and 209; `first()` keeps 20 and discards 209 |
| sum of distinct seat values within `(code, major)` | 3,847 | best available, but still **below** the 3,989 students actually admitted |

Admits exceed the reconstructed quota in all four years (66: 4,118 vs 4,036; 69: 3,989 vs 3,847). **Conclusion: the published file does not permit an exact seat count.** Do not build a headline number on `รับ`.

**Use `ผ่าน` (admits) as the denominator instead.** It is genuinely per-row, sums cleanly, and needs no dedup. Report competition as **applications per admit**:

| | 66 | 67 | 68 | 69 |
|---|---|---|---|---|
| applications (`สมัคร`) | 76,905 | 66,806 | 54,045 | 48,615 |
| admits (`ผ่าน`) | 4,118 | 3,916 | 4,007 | 3,989 |
| **applications per admit** | **18.7** | **17.1** | **13.5** | **12.2** |

Label the numerator **applications, not applicants** — one student may hold up to 10 choices and appear in up to 10 rows. `สมัคร` is application-volume, and no applicant-level deduplication is possible from this file. Any sentence of the form "fewer students applied to Chula" is unsupported; "Chula received 37% fewer applications" is supported.

Row key: `(รหัสหลักสูตร, รายละเอียด, สาขา/วิชาเอก)` is unique **for Chula in all four years (0 duplicates)** but **not nationally** — it collides on 27 / 34 / 32 / 2 rows in 66 / 67 / 68 / 69. Scope the uniqueness assertion to Chula; for national rows, add a positional `row_id` and log the collisions rather than dropping them.

**Trap 2 — `min_score == 0` means "nobody admitted" at Chula, but *not* nationally.**
For Chula it is a clean rule: `min_score == 0` coincides with `passed == 0` in 100% of cases across all four years (12/12, 10/10, 16/16, 19/19).

Nationally the rule is false. **161–210 rows per year have `min_score == 0` alongside real admits** — mostly private and Rajabhat universities (รังสิต, ราชภัฏอุบลราชธานี, หอการค้าไทย, แม่โจ้ …) whose Admission criteria are not exam-scored, so a genuine floor of 0 sits next to a nonzero max. Those are legitimate data, not artifacts.

So: **filter on `passed > 0` for validity — never on `min_score > 0`.** The national baseline is sensitive to this choice and both versions must be reported:

| national median min | 66 | 67 | 68 | 69 |
|---|---|---|---|---|
| `passed > 0` | 50.64 | 51.75 | 53.85 | 52.66 |
| `passed > 0 & min > 0` | 51.71 | 52.64 | 54.70 | 53.33 |

Roughly a 1-point level shift; the *shape* is the same either way, so conclusions about direction are safe and conclusions about level are not.

Also: **TCAS66 alone has 46 rows with `passed == 0` but `min_score != 0`** (67–69 have zero such rows). Decide an explicit rule for these and state it; they are an internal inconsistency in the 66 file, not a real pattern.

**Trap 3 — most universities score in raw percent, but a few score in T-Score.**
The composite is `Σ (raw_subject ÷ 100) × weight`, weights summing to 100 — so published min/max are on a 0–100 raw-weighted scale. **But KMITL, Chiang Mai, and Thammasat (plus Silpakorn and RMUTT in some years) specify T-Score in their เกณฑ์**, so their published numbers are T-Score-weighted composites. Chula uses raw. Cross-university min-score comparisons involving those universities are apples-to-oranges and must be flagged in-chart, not silently plotted alongside Chula.

### The exam-scale finding (already verified — build on it, don't re-litigate)

ทปอ. publishes a T-Score formula each year, `T = 50 + c·(X − mean)/SD`, and `c` changes every year and differs by exam family:

| | 66 | 67 | 68 | 69 |
|---|---|---|---|---|
| A-Level | 5.72973 | 5.21299 | 6.10840 | 6.42869 |
| TGAT/TPAT | 7.87412 | 8.69031 | 9.85870 | 7.71919 |

**`c` is exactly `50 / max|z|`, where the max runs over every subject in that family that year** — i.e. the scale is pinned by the single most extreme individual score in the whole cohort. Verified against all 8 published coefficients; worst relative error 0.017%, six of eight under 0.001%. In every year the TGAT/TPAT coefficient is driven by TPAT5's *minimum* — one candidate's score sets the scale for everyone.

Two consequences the notebooks should state plainly:

- A T-Score of 60 is not the same achievement in 66 and 69. Any program whose university scores in T-Score has a scale break at every year boundary.
- Even for Chula (raw scoring), subject difficulty moves a lot year to year — A-Level เคมี mean went 18.40 → 19.11 → 25.22 → 22.49; ฟิสิกส์ SD went 10.91 → 13.86 → 12.37 → 9.67. A raw-weighted composite inherits all of that. **This is why the normalized track exists.**

### Preview of what the data says (sanity targets — your pipeline should reproduce these)

- Chula applications fell **37%**: 76,905 (66) → 48,615 (69), while admits stayed almost flat: 4,118 → 3,989. Applications per admit fell **18.7 → 12.2**.
- Yet Chula median min-scores are mostly flat-to-up. That tension — *far fewer applications, no easier to get in* — is the headline the project should explain.
- National median min-score: 51.71 → 52.64 → 54.70 → 53.33 (`passed>0 & min>0` filter; see Trap 2 for the other version).
- Biggest Chula faculty moves 66→69 (median min): วิทยาศาสตร์ **−14.6**, นิเทศศาสตร์ **−8.2**, พาณิชยศาสตร์และการบัญชี **−5.3**; ครุศาสตร์ **+4.7**, รัฐศาสตร์ **+3.7**. These are stable under both filter variants. (วิทยาศาสตร์การกีฬา +27.1 and ทรัพยากรการเกษตร +25.9 are artefacts of near-unfilled 66 programs — check `passed` before reporting them.)
- Chula's 14 faculty names are **byte-identical across all four years** and all 48 stable program codes persist 66→69, so the panel needs no fuzzy matching. Assert this rather than building a crosswalk.

---

## Requirements

### R1 — Reproducible tidy dataset
- `src/load.py` reads all four xlsx and emits one tidy dataframe with a stable schema: `year, univ, campus, code, faculty, program, detail, major, seats, applied, passed, min_score, max_score, min_score_ds, max_score_ds, passed_ds`.
- Year-specific column mapping lives in **one** dict at the top of the module, not scattered.
- Written to `data/processed/admission_long.parquet` (+ `.csv` for eyeballing).
- Asserts that fail loudly: row counts per year match the source; the row key is unique **for Chula**; no `min_score > max_score`; every Chula `min_score == 0` row has `passed == 0`. National key collisions are logged, not asserted away.
- `seats` is loaded but **flagged unreliable** — see Trap 1. Any aggregation of it must go through one clearly-named helper so it cannot be summed by accident.

### R2 — Panel construction
- Assert (do not build) faculty-name stability: the 14 Chula faculty strings are identical across all four years, so an equality assert is sufficient and a crosswalk file is unnecessary. If the assert ever fires, *then* add the crosswalk.
- Emit `data/processed/chula_panel.csv` — the balanced panel over the 48 codes present in all four years, used by the model.

### R3 — Exam-scale normalization
- Load `exam_subject_stats.csv` + `tscore_coefficients.csv`.
- Reproduce the `c = 50 / max|z|` check as a **test**, not prose — it is the strongest available validation that the transcription is correct.
- Produce a per-year **cohort difficulty index** for each exam family (e.g. enrolment-weighted mean of subject means, and separately the mean SD) so charts can show "the papers got easier/harder" beside "the bar moved".
- Produce, for each Chula program-year, a **within-year percentile rank** of its min score against the national distribution of that year. This is the scale-free comparison track and is the primary defence against exam drift.

### R4 — Visualization
Charts must be readable in Thai. Set a Thai-capable font once in a shared helper (`src/viz.py`) — check `fc-list :lang=th`; install `fonts-thai-tlwg` or bundle **Sarabun**/**Noto Sans Thai** if absent, and assert the glyphs render rather than silently emitting tofu boxes.

Required figures:

1. **Faculty small-multiples** — 14 panels, min & max score vs year, national median as a ghost line behind each. Raw scale.
2. **The same grid on percentile rank** — placed directly beneath, so raw-vs-normalized divergence is visible at a glance.
3. **Major-level detail within a faculty** — one function, `plot_faculty(name)`, drawing every program in that faculty; run it for วิศวกรรมศาสตร์, อักษรศาสตร์, รัฐศาสตร์ at minimum.
4. **Min–max spread** — the gap between max and min per program over time. A narrowing spread means the cohort is bunching; worth its own chart.
5. **Competition panel** — applications, admits, and applications-per-admit for Chula vs each peer, 66→69. This carries the headline finding. Do **not** plot seats (Trap 1); axis label must read "applications", not "applicants".
6. **Peer comparison** — Chula vs Mahidol, Thammasat, Kasetsart, Chiang Mai, Khon Kaen, KMITL, KMUTT, Silpakorn. **T-Score-scoring universities must be visually marked** (distinct linestyle + legend note), per Trap 3.
7. **Exam-difficulty strip** — subject means/SDs by year, plus the T-Score coefficient and which subject drove it. This is the "why raw scores lie" exhibit.
8. **DS effect** — distribution of `min_score − min_score_ds` for 67–69, showing how much Double Sorting lowers the floor.

Use a single consistent palette and one style module; do not restyle per notebook.

### R5 — Model
Target: **program-level min score for TCAS70, with an honest interval.**

The binding constraint is n = 4 observations per program. The design must respect that:

- **Baselines first, and report them**: (a) last value carried forward, (b) program mean, (c) per-program OLS on year. Any complex model that fails to beat these on the holdout is reported as *not* beating them.
- **Primary model: partially-pooled hierarchical linear trend.** Program-level intercept and slope drawn from a faculty-level distribution, faculty from a university-level one. With n = 4 this shrinkage is what makes per-program slopes usable at all. Implement in `numpyro` or `pymc` if available; if the environment resists, a `statsmodels` `MixedLM` with random intercept + random slope on year is an acceptable fallback — say which was used.
- **Covariates**: applications, admits, applications-per-admit, previous-year min, faculty, and the cohort difficulty index from R3. Not seats (Trap 1).
- **Validation**: leave-last-year-out — fit on 66–68, predict 69, report MAE/RMSE against every baseline. Report per-faculty error, not just the pooled number; a good average can hide a faculty the model cannot touch.
- **Output**: `data/processed/forecast_tcas70.csv` with `code, program, faculty, point, lo80, hi80, lo95, hi95, model, beat_baseline (bool)`.

**Read this before writing the model.** Leave-last-year-out leaves **three** observations per program to fit an intercept and a slope — two parameters, one residual degree of freedom. The per-program fit is very close to saturated, and pooling is not a refinement here, it is the only thing making the exercise legitimate. Two consequences:

- The interval will be wide, and that is the correct answer, not a failure. Do not tune until it narrows.
- If the hierarchical model does not beat last-value-carried-forward, **say so and ship LVCF as the recommendation.** With n=4 that is a plausible outcome and reporting it honestly is worth more than a model that wins by construction.

If the backtest is unconvincing, the highest-value fix is not a better model — it is more data. `assets.mytcas.com/maxmin/TCAS{62..65}_maxmin.xlsx` would take the panel from 4 points to 8. Treat that as the first escalation, ahead of any modelling change.

Do **not** ship a deep net as the primary forecaster on 4 points per program. If a PyTorch variant is added later it must be benchmarked against these same baselines on the same split.

### R6 — Notebooks
Numbered, thin, and readable. Heavy lifting lives in `src/`; notebooks call it and narrate.

```
nb/01_clean.ipynb       load, map columns, assert, write parquet
nb/02_explore.ipynb     Chula shape, coverage, the three traps demonstrated with numbers
nb/03_normalize.ipynb   exam stats, coefficient test, percentile-rank track
nb/04_visualize.ipynb   all figures from R4
nb/05_model.ipynb       baselines → hierarchical model → validation → forecast
nb/06_findings.ipynb    the written answer to "what's inside this data"
```

Every notebook: markdown cell at the top saying what it consumes, what it emits, and what it concludes. No cell longer than ~20 lines.

### R7 — Findings writeup
`reports/findings.md` — the analytical payoff, not a method dump. Must address at minimum:

- Why applications to Chula fell 37% while the bar did not fall — demographic decline, earlier-round uptake (รอบ 1/2 portfolio & quota absorbing demand before รอบ 3), fewer choices used per student, or selection effects. **This file cannot distinguish them**: `สมัคร` counts applications, not applicants, so a drop is consistent with fewer students *or* the same students using fewer of their 10 choices. Say that outright rather than implying a demographic cause.
- Which faculties genuinely got harder/easier once exam drift is removed, and where raw and normalized tracks disagree.
- The T-Score coefficient finding and its practical consequence for anyone comparing years.
- What the forecast can and cannot support.

---

## Proposed approach

Assumptions — override any of these if you disagree:

- Python 3.11+, `pandas`, `numpy`, `matplotlib`, `scikit-learn`, `statsmodels`; `numpyro` or `pymc` for the hierarchical model; `openpyxl` for xlsx. `pyarrow` for parquet.
- No database. Parquet + CSV on disk is the whole persistence layer.
- Thai text is kept as-is in the data; only *display* names are romanized, and only where a chart demands it.

Sequence:

1. `src/load.py` + `nb/01_clean.ipynb` — get the tidy panel and the assertions passing. Nothing downstream is trustworthy until R1's asserts are green.
2. `nb/02_explore.ipynb` — reproduce the three traps numerically. These become regression tests.
3. `src/normalize.py` + `nb/03` — exam stats join, coefficient test, percentile track.
4. `src/viz.py` + `nb/04` — Thai font first, then figures.
5. `src/model.py` + `nb/05` — baselines before anything clever.
6. `nb/06` + `reports/findings.md`.

Ship 1–2 before starting 3. The traps are the part most likely to invalidate everything else.

---

## Files / modules affected

```
src/load.py              new — year column mapping, tidy loader, assertions
src/normalize.py         new — exam stats join, percentile ranks, difficulty index
src/viz.py               new — Thai font setup, palette, plot_faculty(), small-multiple helper
src/model.py             new — baselines, hierarchical model, backtest harness
nb/01..06.ipynb          new
nb/tcas-data-clean.ipynb existing — superseded by 01_clean; keep or delete, your call
tests/test_traps.py      new — grain uniqueness, seat dedup, zero-score rule, coefficient identity
data/processed/*.csv     exam_subject_stats.csv + tscore_coefficients.csv already exist — inputs, not outputs
reports/findings.md      new
```

---

## Acceptance criteria

1. `python -m pytest` passes, including:
   - row counts per year = 4670 / 4718 / 4945 / 5104
   - row key `(code, detail, major)` unique **within Chula** in each year; national collision counts equal 27 / 34 / 32 / 2 (regression guard — if these change, the loader changed)
   - Chula `min_score == 0` ⟹ `passed == 0` in all four years
   - the national counter-example still holds: 161 rows in 69 with `min_score == 0` and `passed > 0` (guards against someone "fixing" Trap 2 the wrong way)
   - `c == 50/max|z|` reproduces all 8 published coefficients within 0.05% relative error
2. `nb/01`…`nb/06` run top-to-bottom from a clean kernel with no manual steps.
3. Pipeline reproduces the sanity targets above, **each with its filter stated in the test**: Chula applications 76,905 → 48,615; admits 4,118 → 3,989; national median min 51.71 → 53.33 under `passed>0 & min>0`; คณะวิทยาศาสตร์ median min down 14.58 points (stable under both filters).
4. Every figure renders Thai glyphs correctly — spot-check by opening one PNG, not by trusting that the font was set.
5. `forecast_tcas70.csv` exists, covers all 48 stable Chula codes, and every row carries an interval. The backtest table showing model vs all three baselines is in `nb/05`, and if the model loses, the notebook says so in words.
6. `reports/findings.md` answers the four questions in R7 with numbers attached, and states at least one thing the data cannot determine.

---

## Non-goals

- Rounds 1, 2, 4, 5 — this is รอบ 3 Admission only.
- Predicting an individual student's admission chance. Program-level floors only; a personal-odds calculator needs applicant-level data that does not exist publicly.
- Re-deriving the exam stat CSVs from the images. Already done and verified.
- A web dashboard. Notebooks and PNGs are the deliverable.
- Scraping mytcas. Everything needed is on disk. (For reference, earlier years exist at `assets.mytcas.com/maxmin/TCAS{62..65}_maxmin.xlsx` if extending the panel later — a real option, since n = 4 is the model's main limitation.)

---

## Scope note — a smaller version that gets 90% of the value

The structure above is 4 modules + 6 notebooks + a test suite. If that reads as too much for the payoff, the defensible minimum is:

- **`nb/01_clean` + `tests/test_traps.py`** — non-negotiable. Every number downstream is wrong without them, and the three traps are precisely where a casual analysis would go wrong silently.
- **`nb/04_visualize`** — the faculty small-multiples and the competition panel are the deliverable most people actually want.
- **`reports/findings.md`** — the exam-scale finding and the applications-vs-bar tension stand on their own without any model.

The hierarchical model (R5) is the part most likely to under-deliver relative to effort, given n = 4. Consider building 1 → 4 → findings first, then deciding whether the forecast is still interesting. Nothing in the plan forces the model to be built to make the rest useful.

## Open decision points

1. **TCAS66's single score column is first-processing** — inferred from its 25 May 2023 publication date falling between the two announced processing dates, not from an explicit ทปอ. statement. If that inference is wrong, the 66 point in every series shifts slightly. Low risk, but note it in the writeup.
2. **Peer set** is currently Mahidol / Thammasat / Kasetsart / Chiang Mai / Khon Kaen / KMITL / KMUTT / Silpakorn. Row counts per year are healthy for all (Mahidol thinnest at 68–87). Adjust if you want a different comparison group.
3. **Extending to TCAS62–65** would double the panel depth (4 → 8 points) and is the single highest-leverage change available. Out of scope for v1 only because the files aren't on disk yet. Promote it the moment the backtest disappoints. Caveat: TCAS62–63 predate the TGAT/TPAT system entirely (GAT/PAT era), so the score composite is not comparable — 64–65 are the realistic extension, taking the panel to 6.
4. **Seats (`รับ`) are unreconcilable** (Trap 1) — reconstructed quota comes out *below* actual admits in all four years. Either ทปอ.'s quota column has semantics not documented in the file, or rows share pools in a way the visible columns don't encode. If you need a true seat count, it has to come from each faculty's own ประกาศ, not this file. Flagged rather than solved.
4. **ทปอ. publishes no official formula document** for how คะแนนรวม is computed. The raw-weighting rule is corroborated by university เกณฑ์ announcements and by tutoring-sector documentation, and is consistent with every published value landing in 0–100 — but it is not a primary-source citation. Do not overstate it.

---

## Provenance of `data/processed/`

`exam_subject_stats.csv` (108 rows) and `tscore_coefficients.csv` (8 rows) were transcribed from the ทปอ./mytcas published stat sheets in `data/alevel/` and `data/tgat-tpat/`, plus `T66-TGAT-TPAT-Stat-20230107.xlsx`.

Verification performed:

- All 11 TCAS66 TGAT/TPAT subjects × 7 fields cross-checked against the source xlsx — **0 mismatches**.
- Structural checks: 16 A-Level subjects × 4 years, 11 TGAT/TPAT subjects × 4 years, unique subject codes, TGAT1/2/3 examinee counts equal to TGAT, TPAT21/22/23 equal to TPAT2 — all pass.
- Range checks: `min ≤ mean ≤ max`, `min ≤ median ≤ max`, `SD > 0`, scores within [0, 100], `N > 0` — all pass.
- The `c = 50/max|z|` identity reproduces all 8 published coefficients (worst error 0.017%). This independently validates the mean/SD/min/max of the driving subject in each family-year to ~4 significant figures.

Known limitation: non-driving subjects are validated only by the structural and range checks above, not to the digit. If a downstream result hinges on one specific subject's mean or SD, re-read that cell from the source image before publishing it.
