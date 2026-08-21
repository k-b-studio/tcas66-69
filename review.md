# Scrutinize review — TCAS รอบ 3 Admission analysis

Cold end-to-end review of `src/`, `nb/`, `tests/`, `specs/`, `reports/` at
`33e0035` + uncommitted `nb/06_polisci.ipynb`. Method: `scrutinize` — question
the intent first, then trace the real code path, then verify each claim against
the data rather than against the prose.

Every number below was recomputed from `data/TCAS{66..69}_maxmin.xlsx` through
`src.load`, not read off the write-ups. `python -m pytest` passes 93/93 at the
time of review.

**Verdict: fix-then-ship.** The analysis is sound, the traps work, and the
headline conclusions survive every robustness check I threw at them. Three
things need fixing before the write-ups are quotable: two faculty numbers in
`reports/findings.md` are composition artefacts that `nb/06` already knows how
to detect, the percentile track quietly violates the project's own Trap 3, and
the model ships without the covariates R5 requires without declaring it.

---

## 1. Intent, and whether a simpler thing would do

**The goal, in one sentence:** separate real competition change from exam-scale
drift and file-format drift, so that "how much harder is it to get into Chula"
has a defensible answer per faculty, plus a forecast honest about n = 4.

That goal is real and the artifact is well-aimed at it. The mandatory
simpler-alternative pass, though:

- **The spec offered a 90% version** (`nb/01` + `tests/test_traps.py` + `nb/04`
  + findings) and explicitly called R5 "the part most likely to under-deliver".
  That judgement was correct on effort, and the model still earned its place —
  but for a reason the spec did not anticipate. It did not produce a forecast
  worth using; it produced a *negative result* (`hierarchical` loses to LVCF by
  36%) that is now the most defensible claim in the report. Keep it. Do not
  extend it.
- **The highest-value work per line is not the model — it is `nb/06`.** The
  route-composition analysis is the only part of the project that found a
  *reported number to be wrong*, and it was not in the spec at all. Finding 2
  below is the argument for propagating that method instead of adding
  modelling.
- **The genuinely highest-leverage change is still the one both the spec and
  README already name**: pull `TCAS{64,65}_maxmin.xlsx` to take the panel from
  4 points to 6. Nothing in the modelling layer can substitute for it. It is
  blocked only by the "no scraping" non-goal, which a manual download satisfies.

No simpler restructuring would preserve what this project actually delivers.
The scope is justified.

---

## 2. Findings

Ordered by severity. Each is framed as the loop you asked for: the outsider's
cold read, the insider's best rebuttal, and what survives the exchange.

### BLOCKER — Route churn makes two faculty headlines in `findings.md` wrong, and `nb/06` already knows it

**Outsider.** `reports/findings.md` §2 tabulates a raw Δ per faculty. Those are
row medians over rows with admits. `nb/06` §8 proves for รัฐศาสตร์ that this
statistic is contaminated when the set of published routes changes — the
faculty's quoted **+3.7** is really **+1.7** once composition is controlled,
because รัฐประศาสนศาสตร์'s cheap routes stopped admitting anyone and so left
the median. The bottom of the distribution was deleted, not raised.

The notebook then writes, correctly: *"any faculty containing a restructured
program needs the same check."* **That check was never run on the other 13.**

**Insider.** "รัฐศาสตร์ is a known special case — one code, routes packed into
`รายละเอียด`. Most Chula faculties have stable route menus, which is exactly
what §8 says. And `findings.md` §8 explicitly declines to call it a defect."

**Resolution — I ran the check on all 14.** Same statistic (row median),
two row-sets: all scored rows, versus only the `(major, detail)` routes scored
in *both* 66 and 69.

| faculty | quoted Δ | like-for-like Δ | composition effect | common routes |
|---|---|---|---|---|
| สำนักวิชาทรัพยากรการเกษตร | +25.88 | +17.04 | **+8.83** | 1 of 4 |
| คณะครุศาสตร์ | +4.72 | **+8.75** | **−4.03** | 17 of 23 |
| คณะรัฐศาสตร์ | +3.74 | **+0.23** | **+3.51** | 15 of 23 |
| คณะวิศวกรรมศาสตร์ | +2.71 | +4.78 | −2.07 | 1 tuple / 9 of 10 rows |
| คณะพาณิชยศาสตร์และการบัญชี | −5.31 | −3.92 | −1.39 | 3 of 7 |
| **คณะวิทยาศาสตร์** | **−14.58** | **−14.43** | **−0.15** | 2 of 17 |
| คณะอักษรศาสตร์ | −0.28 | −0.19 | −0.09 | 9 of 10 |
| จิตวิทยา · นิติศาสตร์ · นิเทศศาสตร์ · สถาปัตย์ · สหเวช · เศรษฐศาสตร์ · วิทยาศาสตร์การกีฬา | — | — | **0.00** | route set identical |

Three things fall out, and they do not all favour the same side:

1. **The headline survives.** คณะวิทยาศาสตร์ −14.58 → −14.43. The project's
   biggest claim is composition-robust. So is อักษรศาสตร์, and seven faculties
   have literally identical route sets in both years — zero effect by
   construction.
2. **รัฐศาสตร์ is worse than `nb/06` reported.** A second, independent control
   (like-for-like routes, rather than the notebook's floor-based aggregators)
   puts it at **+0.23**, not +1.7 and certainly not +3.7. Both controls agree
   the quoted number is mostly artefact; they disagree on how much is left.
3. **ครุศาสตร์ moves the *other* way.** Quoted +4.72, like-for-like **+8.75**.
   Composition is *understating* it — six routes scored in 66 dropped out by 69,
   including ศิลปศึกษา at a 56.54 floor. `findings.md` lists ครุศาสตร์ as a
   +4.7 riser; on a stable route set it is nearly double that.

That asymmetry is the real point. Composition churn is not a one-way bias that
can be waved off as conservative — it moves quoted numbers in both directions.

**Suggested change.** Add a `composition_effect()` helper to `src/normalize.py`
implementing the like-for-like control, run it for all 14 faculties, and put the
corrected column in `findings.md` §2 beside the raw one. Where `common` is small
(ทรัพยากรการเกษตร, พาณิชยศาสตร์, วิทยาศาสตร์) say so — the control is itself
noisy there. Lock the four material cases with a test in the style of
`test_faculty_median_moves_66_to_69`.

---

### MAJOR — The percentile track violates the project's own Trap 3

**Outsider.** `src/normalize.py:37` `national_percentile_rank` ranks each
program's `min_score` inside its own year's national distribution — every row
with `passed > 0`. Trap 3 says KMITL, Chiang Mai, Thammasat, Silpakorn and
RMUTT publish **T-Score-weighted** composites, that these are not comparable in
level to Chula's raw-percent scores, and that they must never be plotted at the
same level. `src/viz.py` honours that scrupulously — dashed lines, square
markers, a whole explanatory panel in figure 06.

The percentile rank then does exactly the forbidden comparison, invisibly: it
ranks Chula's raw score *against a pool containing those rows*.

| year | pool (passed>0) | T-Score rows | share | pool median | T-Score median |
|---|---|---|---|---|---|
| 66 | 4,099 | 593 | 14.5% | 50.64 | 52.05 |
| 69 | 4,498 | 708 | **15.7%** | 52.66 | 53.84 |

The contaminating share is not stable — it grows 14.5% → 15.7% — which is the
exact shape of thing that manufactures a fake trend, and it is the mechanism the
project is most alert to everywhere else.

**Insider.** "The percentile track defends against *exam drift*, not scale
mixing. It is a within-year rank, so any monotone rescaling of the composite
washes out. And these are 15% of rows sitting near the middle of the
distribution — the effect on a rank is second-order."

**Resolution — the insider is substantially right, and it should still be
fixed.** Four pool definitions, Chula median percentile:

| pool | 66 | 67 | 68 | 69 | 66→69 |
|---|---|---|---|---|---|
| as shipped | 77.80 | 75.87 | 81.11 | 78.03 | **+0.24** |
| like-for-like codes only | 79.10 | 77.38 | 81.32 | 79.59 | +0.49 |
| T-Score universities removed | 75.78 | 73.71 | 79.02 | 75.41 | **−0.38** |
| both corrections | 77.10 | 75.32 | 79.22 | 77.28 | +0.18 |

- **The conclusion holds.** "Applications fell 37% and the bar did not fall" is
  true under all four pools: the 66→69 move is between −0.4 and +0.5 in every
  one. This is not a result that reverses.
- **The quoted numbers do not hold.** `README.md` and `findings.md` both print
  the level to one decimal (77.8 → 78.0). That decimal is an artefact of a pool
  choice the project's own Trap 3 forbids; the honest level is ~2 points lower
  throughout.
- **Faculty verdicts are robust.** No sign flips across 14 faculties. Largest
  shift is วิทยาศาสตร์ −35.5 → −30.7 — still the collapse the report describes.
  จิตวิทยา (−1.8 → −2.3) and นิติศาสตร์ (−1.0 → −1.6) keep their reported
  raw-vs-normalized sign flip; that finding is real.

Note also that the project *does* apply a like-for-like correction — but only to
the applications analysis (`findings.md` §1, the 2,848-code panel). The
percentile track, which carries §2's conclusions, gets no such correction. The
two analyses hold themselves to different standards.

**Suggested change.** Give `national_percentile_rank` an explicit
`pool: {"all", "raw_scale", "like_for_like"}` argument defaulting to
`raw_scale` (T-Score universities excluded), and state the pool in the docstring
and in every figure caption that uses it. Re-quote the levels in `README.md` and
`findings.md` from the corrected pool, and add the sensitivity table above to
`findings.md`'s data-quality section — it strengthens the claim rather than
weakening it, because the conclusion survives all four.

---

### MAJOR — The model ships without R5's covariates, and this is not in the deviations list

**Outsider.** `src/model.py:49` `build_panel` builds `diff_alevel`,
`diff_tgat`, `prev_min_score`, `prev_applied`, `prev_passed`,
`prev_apps_per_admit`. `src/model.py:100` is the only formula in the file:

```python
_FORMULA = "min_score ~ year_c + C(faculty)"
```

Not one of those six columns enters any model. R5 requires: *"Covariates:
applications, admits, applications-per-admit, previous-year min, faculty, and
the cohort difficulty index from R3."* Only `faculty` made it in.

Worse, `tests/test_model.py:43-47` asserts the columns exist and are non-null,
and `nb/05` displays `diff_alevel` in a preview table. A reader has three
independent signals that the difficulty index is part of the model. It is not.

**Insider.** "The docstring explains that a real forecast cannot use TCAS70's
own applications, so covariates must be lagged, which costs a year of a 4-year
panel. And the model *loses to LVCF anyway* — adding covariates to a model
already beaten by carry-forward would not change the recommendation."

**Resolution — the reasoning is right and the omission is still undeclared.**
The README lists "Deviations, all deliberate" with three entries (notebooks
02/03/06, MixedLM instead of numpyro, rolling origin instead of single holdout).
This is a fourth, and it is the one a reader is most likely to assume was
handled, because the covariate columns are visibly built and tested.

It also leaves a real hole in the argument. `findings.md` §4 concludes *"at
n = 4, estimating a trend costs more than it earns"* — a claim about **trend
freedom**, supported by a clean monotone ordering across five methods. That
ordering says nothing about whether a *level* model with the cohort difficulty
index would help, because no such model was ever run. The stated conclusion is
broader than the evidence.

**Suggested change.** Cheapest honest fix: add one row to the deviations list
and one sentence to `findings.md` §4 scoping the claim to trend estimation.
Better fix, ~15 lines: run one `hier_no_slope` variant with `+ diff_alevel`
through the existing `rolling_backtest`, and report it. It will almost certainly
lose too — at which point the claim is supported rather than assumed, and the
six unused columns have a reason to exist.

---

### MODERATE — Every program gets an identical forecast interval

`src/model.py:229` `forecast` takes global quantiles of the pooled error
distribution, so all 48 programs receive the same band: **80% width 16.79 for
every row, 95% width identical too** (verified against
`data/processed/forecast_tcas70.csv` — `nunique() == 1`).

Per-program volatility is not uniform: SD of `min_score` across the panel runs
from **1.94 to 16.15, an 8.3× spread**. A program that has sat within 2 points
for four years gets the same ±8.4 as one that swings 16.

The docstring defends the *empirical* choice well — with n = 4 the model's own
variance estimate is not credible, and the rolling-origin record is real
evidence. That argument is sound and I would keep the empirical approach. It
does not, however, argue for a *flat* band.

`test_interval_is_honestly_wide` asserts mean width > 10, which a flat band
passes trivially; nothing tests that the band varies.

**Suggested change.** Scale the pooled quantiles by each program's own
dispersion (e.g. its residual SD around LVCF, shrunk toward the pooled value —
shrinkage being the one tool the project already trusts at this n). If you keep
the flat band, say so explicitly in `findings.md` §4, which currently reads as
though the interval is per-program.

---

### MODERATE — The winner-selection gate contradicts the project's own argument

`src/model.py:355`:

```python
best_baseline = summary.loc[list(BASELINES), "MAE"].min()   # single holdout
beat = bool(hier_mae < best_baseline)                       # single holdout
winner = "hierarchical" if beat else str(pooled.index[0])   # pooled
```

`summary` is the **single** 68→69 holdout. `pooled` is the **two-origin**
result. The comment immediately above explains, convincingly, that a single
holdout is unreliable because every method's bias flips sign between origins —
and then the `beat` gate uses exactly that unreliable single holdout.

Harmless today: `hierarchical` loses at both origins, so the gate never fires
and `test_hierarchical_does_not_beat_baselines` would fail loudly first. But if
a future panel (TCAS64–65, say — the change the project most wants) let
`hierarchical` win the single holdout while losing pooled, it would ship on the
evidence the project itself rejects.

**Suggested change.** Compute `beat` from `pooled` too, so selection uses one
standard of evidence. Two-line change; keep the single-holdout table in the
output since `findings.md` §4 reports it.

---

### MINOR — `README.md` no longer describes the repository

`README.md:168` states: *"Notebooks 02, 03 and 06 were not written."* But
`nb/06_polisci.ipynb` exists, is 63 cells, and has shipped:

- `reports/figures/09..13_polisci_*.png` — five figures, absent from the README
  figure table (which stops at `08`)
- `data/processed/polisci_major_panel.csv`, `polisci_route_panel.csv` — absent
  from the README layout tree
- the composition finding of Finding 1 — absent from `reports/findings.md`
  entirely (`grep -i "polisci\|composition\|route"` returns nothing)

`findings.md` is billed as "the written answer" and does not contain the
project's most interesting methodological result.

**Suggested change.** Update the README layout tree, figure table, and status
section; add a `findings.md` section for the composition result once Finding 1's
all-faculty version is done. These land together — the corrected §2 table *is*
the propagation of `nb/06`.

---

### MINOR — `nb/06`'s outputs are the only unguarded artefacts in the project

Everything else is regression-locked: row counts, collision counts, seat-dedup
failures, both sides of the zero-score rule, the sanity targets, the
`c = 50/max|z|` identity, forecast shape and interval nesting. The polisci
panels have no tests at all — no balance assertion on the 4×4 major panel, no
guard on the HHI series, nothing pinning the +3.7 vs +1.7 gap that is the
notebook's entire conclusion.

Given the project's own standard ("these are the tests that stop a casual
analysis from being silently wrong"), this is the gap most out of character.

**Suggested change.** `tests/test_polisci.py`: assert the elective parse
round-trips, that quota == admits in all 16 major-years, and that the
row-median-vs-composition-controlled gap for รัฐศาสตร์ is what the notebook
claims. Move the parse out of the notebook into `src/` so it is importable.

---

### NIT — `nb/06` cell 59

`` Data in TCAS68 for ``คณิตประยุกต์ 2` is missing. `` — unbalanced backticks,
and it reads as a leftover note rather than a finding. §1 already documents this
properly ("คณิตศาสตร์ประยุกต์ 2 is missing one year — รัฐประศาสนศาสตร์ dropped
it in TCAS68 and brought it back in 69"). Delete the stray line.

---

## 3. What I traced and found solid

Stated so you can judge whether the review covered the surface you cared about.
No rubber stamps — these were checked, not assumed.

- **The three traps hold up completely.** I re-derived the seat inflation
  (7,639 vs 3,989 admits), the `groupby(code).first()` failure on
  `10010122904301A`, the reconstruction-below-admits result in all four years,
  the Chula-only zero-score rule, and the 161–210 national counter-examples.
  Each is empirically true and correctly tested. `reconstructed_seats`'s
  docstring is a model of how to document an unusable column.
- **The `c = 50/max|z|` identity.** Reproduces all 8 published coefficients;
  the strongest available validation of the transcription, and correctly
  expressed as a test rather than prose. The TPAT5-minimum finding is real and
  genuinely striking.
- **`chula()` exact matching.** The substring trap is real (48,615 vs 49,976)
  and tested. Same for `viz.PEERS` exact resolution.
- **The Thai font layer.** `resolve_thai_font` reads the font file's own charmap
  and then does a live render escalating matplotlib's missing-glyph warning to
  an error. `test_named_font_is_not_trusted_blindly` documents that `Sarabun`
  resolves to DejaVu on this machine. This is the correct paranoia, correctly
  implemented.
- **The negative model result.** The five-method ordering is monotone in trend
  freedom, partial pooling beats no pooling at both origins, and the
  `program_mean` single-holdout win is correctly dismissed (paired t p = 0.38,
  bootstrap CI spanning zero). `test_hierarchical_does_not_beat_baselines` pins
  the real finding rather than a hoped-for one — the single best testing
  decision in the project.
- **The two spec corrections.** DS raises the floor in ~8% of rows
  (333/337/352) and the min–max spread does not narrow monotonically
  (11.29 → 7.65 → 9.43 → 10.14). Both contradict the spec, both are right, and
  `test_ds_usually_lowers_the_floor_but_not_always` names the spec as wrong in
  its own docstring.
- **The applications-vs-applicants discipline.** Held consistently across
  README, spec, findings, figure captions and axis labels. Rare.
- **93/93 tests pass**, ~20s, no warnings.

---

## 4. Improvements, in priority order

| # | Change | Effort | Why it ranks here |
|---|---|---|---|
| 1 | Propagate `nb/06`'s composition control to all 14 faculties; correct §2 of `findings.md` | ~half a day | Two quoted numbers are currently wrong in opposite directions |
| 2 | Add `pool=` to `national_percentile_rank`, default T-Score-excluded; re-quote levels; publish the sensitivity table | ~2 hours | Removes a self-inflicted Trap 3 violation; the conclusion survives, so this only strengthens it |
| 3 | Declare the covariate deviation; optionally run one `+ diff_alevel` variant | ~1 hour | Closes the gap between what §4 claims and what was tested |
| 4 | Per-program forecast intervals, or say plainly that the band is flat | ~2 hours | 8.3× volatility spread currently hidden |
| 5 | `beat` gate from pooled evidence | 2 lines | Removes a latent contradiction before the panel grows |
| 6 | README + `findings.md` catch up with `nb/06` | ~1 hour | The best result in the project is undocumented |
| 7 | `tests/test_polisci.py`; lift the elective parse into `src/` | ~2 hours | Only unguarded artefacts in an otherwise rigorously tested repo |
| 8 | **Pull `TCAS{64,65}_maxmin.xlsx`** | ~half a day | Still the highest-leverage change available; 4 → 6 points is the difference between an inestimable slope and a marginal one |

Items 1–3 are what "fix-then-ship" means: until they are done, `findings.md`
should not be circulated as the written answer, because two of its faculty
numbers are artefacts and one of its methods contradicts its own stated rules.
Items 4–7 are hygiene. Item 8 is the only thing that changes what the project
can conclude, and both the spec and README already identified it — the review
merely confirms that nothing in the modelling layer substitutes for it.

---

## 5. The one structural observation

The project's greatest strength is that it repeatedly went looking for ways its
own numbers could be wrong — the seat reconstruction, the zero-score
counter-example, the DS direction, the single-holdout instability, the
`program_mean` bootstrap. Each time it found something and wrote it down.

Findings 1 and 2 are the same discipline applied one level further out, to
statistics the project stopped auditing once they were computed: the faculty row
median and the national percentile pool. Both were treated as the *answer* to a
bias rather than as estimators with biases of their own. `nb/06` had already
noticed this for one faculty and stated the general rule; the gap is that the
rule was written down and not executed.

That is a good failure mode to have. It means the fix is propagation, not
rework.
