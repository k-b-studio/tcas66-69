# What's inside the TCAS รอบ 3 data, TCAS66–69

Chulalongkorn, four years of Admission min/max score files. Every figure below
is reproduced by `nb/01_clean` → `nb/04_visualize` and guarded by
`tests/test_traps.py`. Filters are stated wherever they change a number.

---

## The one-paragraph version

Applications to Chula fell **37%** in four years while the number of students it
admitted stayed flat, so competition per admitted student dropped from 18.7
applications to 12.2 — and the entry bar did not fall. That is not a
demographic story: on a like-for-like basis the rest of the sector lost only
**4%** of its applications over the same period, and KMITL, Mahidol, KMUTT and
Silpakorn all *gained* a quarter to a half. Chula lost demand that the sector
did not lose. Meanwhile the raw score series systematically flatters Chula:
once each program is ranked inside its own year's national distribution, every
faculty looks worse than its raw points suggest, and two faculties reverse sign
outright. And with only four observations per program, the forecast is honest
about its limits — a partially-pooled hierarchical model loses to
last-value-carried-forward, so LVCF is what ships, with an 80% interval nearly
17 points wide.

---

## 1. Applications fell 37% and the bar did not fall. Why?

The raw shape:

| | 66 | 67 | 68 | 69 |
|---|---|---|---|---|
| applications (`สมัคร`) | 76,905 | 66,806 | 54,045 | 48,615 |
| admits (`ผ่าน`) | 4,118 | 3,916 | 4,007 | 3,989 |
| **applications per admit** | **18.7** | **17.1** | **13.5** | **12.2** |
| median min score (`passed>0`) | 64.43 | 63.66 | 69.34 | 66.88 |
| median percentile rank | 77.8 | 75.9 | 81.1 | 78.0 |

Competition per admit fell by a third. The bar went **up** 2.4 raw points, and
on percentile rank it did not move at all (77.8 → 78.0). Four years of sharply
falling demand produced no measurable easing.

### It is not demographics

This is the question the spec expected to be unanswerable, and it is *partly*
answerable. Restricting to the 2,848 program codes present in all four years —
a strict like-for-like panel that removes any effect of the file's growing
coverage:

| like-for-like applications, index 66 = 100 | 66 | 67 | 68 | 69 |
|---|---|---|---|---|
| Chula | 100.0 | 86.9 | 70.3 | **62.7** |
| everyone else | 100.0 | 124.0 | 105.7 | **95.9** |

The rest of the sector lost 4.1%. Chula lost 37.3%. Nationally, admits *grew*
23% (85,290 → 105,058) while total applications stayed flat. A shrinking cohort
cannot produce that pattern — it would drag everyone down together.

The demand went somewhere specific:

| 66 → 69 applications | change |
|---|---|
| KMITL | **+59.8%** |
| Mahidol | +32.7% |
| KMUTT | +25.6% |
| Silpakorn | +25.4% |
| Kasetsart | −11.0% |
| Khon Kaen | −28.4% |
| Chiang Mai | −30.4% |
| Thammasat | −34.6% |
| **Chulalongkorn** | **−36.8%** |

The sector split in two. The old-guard comprehensive universities lost a third
of their applications; the technology and health institutes gained.

### What this file still cannot determine

**Why Chula specifically lost demand.** `สมัคร` counts *applications*, not
*applicants* — one student holds up to 10 choices and can appear in up to 10
rows, and no applicant-level deduplication is possible. So all of these remain
consistent with the data:

- students increasingly filled รอบ 1/2 (portfolio and quota) and never reached
  รอบ 3;
- the same students applied but spent fewer of their 10 choices on Chula;
- preferences shifted toward the institutes that gained.

Ruling *in* one of these needs applicant-level data that is not published.
What the data does rule out is a pure demographic decline, because the sector
ex-Chula barely moved.

**A supportable sentence** is "Chula received 37% fewer applications."
**An unsupportable one** is "37% fewer students applied to Chula."

### Losing applications did not lower the bar — at the faculty level either

| faculty | applications 66→69 | per-admit 66→69 | raw Δ | percentile Δ |
|---|---|---|---|---|
| วิศวกรรมศาสตร์ | **−64.6%** | 9.9 → 4.5 | **+2.7** | **+2.5** |
| วิทยาศาสตร์ | −8.3% | 16.9 → 14.3 | **−14.6** | **−35.5** |

Engineering's competition more than halved and its floor went *up*. Science
barely lost demand and its floor collapsed. Across the 12 non-outlier
faculties the correlation between applications lost and percentile moved is
**−0.47** (Spearman −0.32, n = 12) — weak, and of the opposite sign to the
naive expectation. Including the two tiny undersubscribed faculties flips it to
+0.73, which is why that correlation should not be quoted: it is an artefact of
two programs.

**The bar is not a simple function of how many people applied.** Whatever sets
these floors — subject weightings, criteria changes, who self-selects into
applying — is largely invisible in this file.

---

## 2. Which faculties actually got harder, once exam drift is removed

Raw points and percentile rank disagree systematically, because the national
median rose faster than Chula's floors (50.64 → 52.66 on `passed>0`). A Chula
program can gain raw points and still lose ground.

| faculty | raw Δ | percentile Δ | divergence |
|---|---|---|---|
| คณะวิทยาศาสตร์ | −14.6 | **−35.5** | −20.9 |
| คณะพาณิชยศาสตร์และการบัญชี | −5.3 | **−14.2** | −8.9 |
| คณะสถาปัตยกรรมศาสตร์ | −2.7 | **−10.1** | −7.4 |
| คณะนิเทศศาสตร์ | −8.2 | −9.3 | −1.1 |
| คณะอักษรศาสตร์ | −0.3 | −2.6 | −2.3 |
| **คณะจิตวิทยา** | **+0.9** | **−1.8** | −2.7 |
| **คณะนิติศาสตร์** | **+1.3** | **−1.0** | −2.3 |
| คณะเศรษฐศาสตร์ | +2.1 | +0.9 | −1.2 |
| คณะวิศวกรรมศาสตร์ | +2.7 | +2.5 | −0.2 |
| คณะรัฐศาสตร์ | +3.7 | +2.2 | −1.5 |
| คณะครุศาสตร์ | +4.7 | +2.4 | −2.3 |
| คณะสหเวชศาสตร์ | +3.5 | +3.7 | +0.2 |
| สำนักวิชาทรัพยากรการเกษตร | +25.9 | +33.6 | +7.7 |
| คณะวิทยาศาสตร์การกีฬา | +27.1 | +43.7 | +16.6 |

### Where raw and normalized disagree

**Two faculties flip sign.** จิตวิทยา (+0.9 raw, −1.8 percentile) and
นิติศาสตร์ (+1.3 raw, −1.0 percentile) gained raw points while slipping against
the national field. Anyone reading the raw series alone concludes they got
harder to enter. They did not; the country moved up faster.

**Only one faculty improves more on the normalized track** than the raw one
(สหเวชศาสตร์, +0.2). For all others the raw number is the more flattering of
the two. Any account of Chula built on raw min scores is biased optimistic.

### คณะวิทยาศาสตร์ is the headline, and it is uniform

Its median floor fell 59.56 → 44.97 raw, and its percentile rank fell from the
**69.6th to the 34.1st** — the only Chula faculty to cross below the national
median. This is not an outlier effect: **all 17 of its 17 programs fell**,
median −13.2 points, from −0.9 to −23.8. Meanwhile it admitted *more* students
each year (858 → 929) with applications nearly recovered by 69 (14,530 →
13,323).

A uniform, faculty-wide fall with no matching collapse in demand points to
something structural — a change in criteria, subject weightings, or intake
policy. **This file does not contain เกณฑ์ or weightings, so the cause cannot
be determined from it.** It should be checked against the faculty's own
ประกาศ before anyone attributes it to falling standards.

### The two big risers are a different measurement

วิทยาศาสตร์การกีฬา (+27.1) and ทรัพยากรการเกษตร (+25.9) are real moves off an
undersubscribed base, not artefacts — both filled their TCAS66 seats. But they
drew **1.8** and **3.7** applications per admit in 66 against a Chula-wide
18.7. Their floors were low because almost nobody applied, and normalised once
applicants arrived (วิทยาศาสตร์การกีฬา: 72 applications in 66 → 635 in 67).
Report them with the base rate attached; they do not belong in the same
sentence as the other twelve.

---

## 3. The T-Score coefficient, and why it breaks year-to-year comparison

ทปอ. publishes a T-Score coefficient each year, `T = 50 + c·(X − mean)/SD`:

| | 66 | 67 | 68 | 69 |
|---|---|---|---|---|
| A-Level | 5.72973 | 5.21299 | 6.10840 | 6.42869 |
| TGAT/TPAT | 7.87412 | 8.69031 | 9.85870 | 7.71919 |

**`c` is exactly `50 / max|z|`**, where the max runs over every subject in that
family that year. This reproduces all eight published coefficients — worst
relative error 0.017%, six of eight under 0.001% (`tests/test_traps.py`).

The consequence is not academic. The scale is pinned by **the single most
extreme individual score in the entire cohort**, and in all four years the
TGAT/TPAT coefficient is driven by TPAT5's *minimum* — one candidate scoring
6, then 0, then 9, then 1. One person's paper sets the scale for a million
examinees, and it is re-derived from scratch every year.

**Practical consequence:** a T-Score of 60 is not the same achievement in
TCAS66 and TCAS69. Every university that scores in T-Score — KMITL, Chiang Mai,
Thammasat, plus Silpakorn and RMUTT in some years — has a scale break at every
year boundary. Their series are marked dashed in every chart here; compare
their *shape* over time, never their *level* against Chula's.

Chula scores in raw percent, so it escapes the coefficient — but not paper
difficulty. A-Level เคมี's mean went 18.40 → 19.11 → 25.22 → 22.49; ฟิสิกส์'s SD
went 10.91 → 13.86 → 12.37 → 9.67. A raw-weighted composite inherits every bit
of that. **This is why the percentile track exists, and why section 2's
conclusions rest on it rather than on raw points.**

One caveat on the composite itself: ทปอ. publishes no formula document for how
คะแนนรวม is computed. The raw-weighting rule (`Σ (raw ÷ 100) × weight`, weights
summing to 100) is corroborated by university เกณฑ์ announcements and by every
published value landing in 0–100, but it is not a primary-source citation.

---

## 4. What a forecast can and cannot support

**The hierarchical model lost. Last-value-carried-forward ships.**

Leave-last-year-out — fit on TCAS66–68, predict TCAS69, all 48 programs:

| method | per-program trend | MAE | RMSE |
|---|---|---|---|
| `program_mean` | none | **4.89** | 6.66 |
| `hier_no_slope` | level pooled, one global slope | 5.09 | 6.63 |
| `lvcf` | none | 5.39 | 6.61 |
| `hierarchical` | slope, partially pooled | 6.66 | 8.04 |
| `program_ols` | slope, unpooled | 8.02 | 9.73 |

The partially-pooled model is **36% worse** than the best baseline. That is the
result, not a defect to tune around.

### The ranking is the finding

The error ordering is monotone in how much freedom each method has to fit a
per-program trend. Partial pooling works exactly as advertised — the shrunk
slope beats the unpooled slope by 1.4 MAE, at both backtest origins. It simply
cannot rescue a slope estimated from three or four points. **At n = 4,
estimating a trend costs more than it earns**, and the more trend freedom a
method has, the more it costs.

### Why LVCF and not `program_mean`

`program_mean` wins the single spec holdout, but the panel median *oscillates*
rather than trends — 58.71 → 53.94 → 57.97 → 53.50 — and every method's bias
flips sign between origins (−0.4 into the rising year 68, +3.2 into the falling
year 69). A single held-out year therefore rewards whichever method happened to
lean the right way that year.

Rolling the origin to score both available transitions:

| method | 67→68 | 68→69 | pooled MAE |
|---|---|---|---|
| **`lvcf`** | 5.89 | 5.39 | **5.638** |
| `program_mean` | 7.13 | 4.89 | 6.012 |
| `hier_no_slope` | 7.46 | 5.09 | 6.277 |
| `hierarchical` | 6.81 | 6.66 | 6.734 |
| `program_ols` | 7.24 | 8.02 | 7.630 |

`lvcf` is the only method stable at both origins. And `program_mean`'s
single-holdout win was never statistically real: paired t **p = 0.38**,
Wilcoxon **p = 0.14**, bootstrap CI for the difference **[−0.60, +1.55]** —
spanning zero. Two tied methods, separated by stability across years.

### What the forecast supports

`data/processed/forecast_tcas70.csv` — 48 programs, every row with an interval.

- **The 80% interval averages 16.8 points wide, the 95% averages 27.3**, on a
  0–100 scale. That is the honest answer at n = 4, and it is still optimistic:
  it is calibrated on two year transitions, both inside the observed regime.
- Intervals are **asymmetric and sit below the point estimate**, because the
  shipped method over-predicts by +1.4 on average across both origins.
- `beat_baseline` is `False` in every row, by design — the column records that
  the model lost.

### What it cannot support

- **Anything about an individual applicant.** These are program-level floors.
  The lowest admitted score says nothing about where a particular student sits,
  and the applicant-level data that would is not published.
- **A confident number for any single program.** With a ±8-point 80% band, the
  forecast distinguishes "roughly 70" from "roughly 50" and little else.
- **Any claim resting on a program's trend.** The backtest says per-program
  trends are not estimable at this depth. A program that has risen three years
  running is not thereby predicted to rise again.

### The highest-leverage fix is data, not modelling

`assets.mytcas.com/maxmin/TCAS{64,65}_maxmin.xlsx` would take the panel from 4
points to 6 — the difference between a slope that cannot be estimated and one
that might be. TCAS62–63 predate TGAT/TPAT entirely, so their composite is not
comparable and they do not help. No deep net was tried; on four points per
program that needs no defending.

*Implementation note:* the spec asks for `numpyro` or `pymc`; neither is
installed in this environment, so this uses the sanctioned `statsmodels`
`MixedLM` fallback — random intercept and slope per program, faculty as a fixed
effect, a two-level approximation to the spec's three-level design. Given that
the model loses to LVCF by a wide margin and the *unpooled* variant loses by
more still, a fuller Bayesian implementation would have to overturn the
direction of the entire gradient to change the conclusion.

---

## Things this data cannot determine

Collected, because each one is a sentence someone will otherwise write without
support:

1. **Whether fewer *students* applied to Chula.** `สมัคร` counts applications;
   one student holds up to 10 choices. The 37% drop is application volume.
2. **Why Chula specifically lost demand** — earlier-round absorption, choice
   reallocation, or preference shift. All three fit the data.
3. **Why คณะวิทยาศาสตร์ fell across all 17 programs.** Criteria and subject
   weightings are not in this file.
4. **How many seats any program actually offered.** `รับ` cannot be summed —
   one code fans out into many rows sharing a quota. The best reconstruction
   comes out *below* actual admits in all four years (66: 4,036 vs 4,118;
   69: 3,847 vs 3,989), so the file is not self-consistent on seats. A true
   count has to come from each faculty's ประกาศ. Every competition figure here
   uses admits as the denominator instead.
5. **Whether TCAS66's single score column is first-processing.** Inferred from
   its 25 May 2023 publication date falling between the two announced
   processing dates, not from an explicit ทปอ. statement. If wrong, the 66
   point in every series shifts slightly.

---

## Two corrections to the project's own assumptions

Both were assumed in the spec and are false in the data:

**Double Sorting does not only lower the floor.** Across TCAS67–69 it lowers
the floor in ~54% of rows with admits, leaves ~38% untouched, and **raises** it
in ~8% (333/337/352 rows nationally). The mechanism is real: when marginal
admits decline their seat, the remaining floor rises — and two TCAS68 Chula
rows go from zero admits to a real DS admit, which necessarily lifts the floor
off zero. Any analysis assuming a one-way move is wrong about one row in
twelve.

**The min–max spread is not steadily narrowing.** Median spread went 11.29 →
7.65 → 9.43 → 10.14 — it collapses in TCAS67 and re-widens most of the way
back. There is no four-year bunching trend to report.

---

## Data quality notes

- **`min_score == 0` means "nobody admitted" at Chula** (100% coincidence with
  `passed == 0`, 12/10/16/19 rows) but **not nationally**: 161–210 rows a year
  have a genuine zero floor beside real admits, mostly private and Rajabhat
  universities whose criteria are not exam-scored. Validity filters here use
  `passed > 0`, never `min_score > 0`. At Chula the two are the same filter,
  which is why every Chula figure is stable under both.
- **National medians shift ~1 point between the two filters** (51.71 → 53.33
  strict; 50.64 → 52.66 lenient) but the shape is identical. Conclusions about
  direction are safe; conclusions about level are not.
- **TCAS66 has 46 national rows** reporting no admits beside a nonzero floor;
  67–69 have none. Left in place and excluded by the standard `passed > 0`
  filter.
- **One genuine ทปอ. error**: TCAS67 ราชวิทยาลัยจุฬาภรณ์ `10320104112101A`
  publishes `min = 46.33, max = 10.0`, while its own DS columns read
  `min = 40.86, max = 46.33`. The real max is 46.33. Left uncorrected and
  logged rather than silently patched.
- Chula's 14 faculty names are byte-identical across all four years and all 48
  of its TCAS66 program codes survive to TCAS69, so the panel needs no fuzzy
  matching or crosswalk.
