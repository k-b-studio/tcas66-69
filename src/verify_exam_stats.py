"""Independent checks on the transcribed exam stats."""
import pandas as pd, numpy as np
df = pd.read_csv("data/processed/exam_subject_stats.csv")
co = pd.read_csv("data/processed/tscore_coefficients.csv")
fail = 0
def chk(cond, msg):
    global fail
    if not cond: fail += 1; print("  FAIL:", msg)

print("== structural ==")
chk(len(df)==108, "expected 108 rows")
for (f,y),g in df.groupby(["exam_family","tcas_year"]):
    chk(g.subject_code.is_unique, f"{f} {y} duplicate subject codes")
chk(df.groupby(["exam_family","tcas_year"]).size().nunique()==2, "inconsistent subject counts")
print(df.groupby(["exam_family","tcas_year"]).size().to_string())

print("\n== range sanity ==")
chk((df["min"] <= df["mean"]).all(), "min > mean somewhere")
chk((df["mean"] <= df["max"]).all(), "mean > max somewhere")
chk((df["min"] <= df["median"]).all() and (df["median"] <= df["max"]).all(), "median outside [min,max]")
chk((df["sd"] > 0).all(), "non-positive SD")
chk((df["max"] <= 100).all() and (df["min"] >= 0).all(), "score outside [0,100]")
chk((df.n_examinees > 0).all(), "non-positive N")

print("\n== TGAT sub-part N consistency (TGAT1/2/3 must match TGAT) ==")
for y in [66,67,68,69]:
    g = df[(df.exam_family=="TGAT/TPAT") & (df.tcas_year==y)].set_index("subject_en")
    chk(g.loc[["TGAT","TGAT1","TGAT2","TGAT3"],"n_examinees"].nunique()==1, f"{y} TGAT parts N mismatch")
    chk(g.loc[["TPAT2","TPAT21","TPAT22","TPAT23"],"n_examinees"].nunique()==1, f"{y} TPAT2 parts N mismatch")
print("  ok")

print("\n== T-Score coefficient hypothesis: c == 50 / max|z| over subjects in family ==")
print(f"{'family':10} {'yr':>3} {'published c':>12} {'50/max|z|':>10} {'rel.err':>9}  driver")
for _, r in co.iterrows():
    g = df[(df.exam_family==r.exam_family) & (df.tcas_year==r.tcas_year)].copy()
    # composite TGAT/TPAT2 rows are aggregates of their parts; keep all — the max is what matters
    g["z_lo"] = (g["mean"] - g["min"]) / g["sd"]
    g["z_hi"] = (g["max"] - g["mean"]) / g["sd"]
    g["zmax"] = g[["z_lo","z_hi"]].max(axis=1)
    top = g.loc[g.zmax.idxmax()]
    implied = 50.0 / top.zmax
    err = abs(implied - r.tscore_coefficient) / r.tscore_coefficient
    side = "max" if top.z_hi >= top.z_lo else "min"
    print(f"{r.exam_family:10} {r.tcas_year:>3} {r.tscore_coefficient:12.5f} {implied:10.5f} {err:8.4%}  {top.subject_en} ({side}={top['max'] if side=='max' else top['min']:g})")
    chk(err < 0.002, f"{r.exam_family} {r.tcas_year} coefficient mismatch {err:.4%}")

print(f"\n{'ALL CHECKS PASSED' if fail==0 else str(fail)+' CHECKS FAILED'}")
