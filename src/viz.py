"""Shared style, Thai font setup, and every figure in R4.

Font policy: matplotlib will happily fall back to DejaVu Sans and emit tofu
boxes for every Thai glyph without raising anything. On this machine
``Sarabun`` is even *listed* by the font manager but resolves to DejaVu when
asked for — so a font is never trusted by name. :func:`setup` resolves a
candidate, checks the font file's own charmap for the codepoints we actually
draw, and then does a live render and fails on matplotlib's missing-glyph
warning. See :func:`verify_thai_rendering`.
"""

from __future__ import annotations

import io
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm
from matplotlib.ft2font import FT2Font

from src.load import CHULA, REPO, TSCORE_UNIVERSITIES, chula
from src.normalize import (
    cohort_difficulty_index,
    load_coefficients,
    load_exam_stats,
    national_percentile_rank,
    tscore_drivers,
)

FIGDIR = REPO / "reports" / "figures"

#: Tried in order. First one whose file actually contains Thai glyphs wins.
THAI_FONT_CANDIDATES = (
    "TH Sarabun New", "TH SarabunPSK", "Noto Sans Thai", "Sarabun",
    "Loma", "Garuda", "Waree", "Thonburi", "Ayuthaya",
)

#: Used to *select* a Thai font: consonants, vowels, tone marks, the
#: thanthakhat, a Thai digit. Thai only — symbols are the fallback's job.
_THAI_PROBE = "คณะวิศวกรรมศาสตร์อักษรศาสตร์ผ่านสมัครคะแนนต่ำสุด๙"

#: Used to *verify the live render*: everything the charts actually draw,
#: including symbols no Thai font is obliged to carry. TH Sarabun New has no
#: U+2192, so the arrow must come from the fallback family — which is exactly
#: what this probe is here to prove.
_RENDER_PROBE = "คณะวิศวกรรมศาสตร์ ผ่าน ๙  -12.5 − 3 → 66→69 ±%"

#: Supplies glyphs the Thai font lacks. matplotlib resolves `font.family` as an
#: ordered stack and falls back per-glyph.
_FALLBACK_FAMILY = "DejaVu Sans"

# --- palette -------------------------------------------------------------
PALETTE = {
    "chula": "#C8102E",       # Chula pink-red
    "chula_soft": "#E8879A",
    "national": "#9AA0A6",    # ghost / reference lines
    "max": "#1B6CA8",         # max-score track
    "min": "#C8102E",         # min-score track
    "accent": "#E8A33D",
    "ok": "#2E8B57",
    "grid": "#DFE1E5",
    "ink": "#202124",
    "muted": "#5F6368",
}

#: Distinct colours for the peer-comparison chart.
PEER_COLORS = [
    "#C8102E", "#1B6CA8", "#2E8B57", "#E8A33D", "#7B4EA3",
    "#00868B", "#B5651D", "#D65DB1", "#5F6368",
]

#: Peer set (R4 fig 6). Exact strings — `contains` would catch
#: ราชภัฏเชียงใหม่ and ราชภัฏธนบุรี, which are different universities.
PEERS = {
    CHULA: "Chulalongkorn",
    "มหาวิทยาลัยมหิดล": "Mahidol",
    "มหาวิทยาลัยธรรมศาสตร์": "Thammasat",
    "มหาวิทยาลัยเกษตรศาสตร์": "Kasetsart",
    "มหาวิทยาลัยเชียงใหม่": "Chiang Mai",
    "มหาวิทยาลัยขอนแก่น": "Khon Kaen",
    "สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง": "KMITL",
    "มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าธนบุรี": "KMUTT",
    "มหาวิทยาลัยศิลปากร": "Silpakorn",
}

YEARS = (66, 67, 68, 69)


# --- font ----------------------------------------------------------------

def _font_path(name: str) -> Path | None:
    """Resolve a family name to a file, refusing silent fallback."""
    try:
        path = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
    except Exception:
        return None
    return Path(path)


def _covers_thai(path: Path) -> bool:
    try:
        charmap = FT2Font(str(path)).get_charmap()
    except Exception:
        return False
    return all(ord(ch) in charmap for ch in _THAI_PROBE if not ch.isspace())


def resolve_thai_font() -> tuple[str, Path]:
    """First candidate whose *file* contains every glyph we draw.

    Raises with an actionable message if none qualifies, rather than letting
    the charts render as tofu.
    """
    tried = []
    for name in THAI_FONT_CANDIDATES:
        path = _font_path(name)
        if path is None:
            tried.append(f"{name}: not installed")
            continue
        if not _covers_thai(path):
            missing = [
                ch for ch in _THAI_PROBE
                if not ch.isspace() and ord(ch) not in FT2Font(str(path)).get_charmap()
            ]
            tried.append(f"{name}: missing {''.join(missing)!r}")
            continue
        return name, path
    raise RuntimeError(
        "No Thai-capable font found. Tried:\n  "
        + "\n  ".join(tried)
        + "\n\nInstall one, e.g.  brew install --cask font-sarabun\n"
        "or download Noto Sans Thai and run "
        "matplotlib.font_manager.fontManager.addfont(<path>)."
    )


def verify_thai_rendering(font_name: str | None = None) -> None:
    """Actually draw Thai text and fail if any glyph is missing.

    The charmap check above is static; this is the dynamic one. matplotlib
    emits ``UserWarning: Glyph N (...) missing from font(s) ...`` at draw time,
    which is exactly the tofu condition, so it is escalated to an error. Also
    asserts the render is not blank.
    """
    fig = plt.figure(figsize=(4, 1))
    kwargs = {"fontfamily": font_name} if font_name else {}
    fig.text(0.5, 0.55, _RENDER_PROBE[:24], ha="center", size=18, **kwargs)
    fig.text(0.5, 0.15, _RENDER_PROBE[24:], ha="center", size=18, **kwargs)

    buf = io.BytesIO()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(buf, format="png", dpi=72)
    plt.close(fig)

    missing = [str(w.message) for w in caught if "missing from font" in str(w.message)]
    if missing:
        raise RuntimeError(
            "Thai glyphs did not render (tofu). matplotlib reported:\n  "
            + "\n  ".join(sorted(set(missing))[:5])
        )

    buf.seek(0)
    img = plt.imread(buf)
    ink = (img[..., :3].min(axis=-1) < 0.5).sum()
    if ink < 200:
        raise RuntimeError(f"Thai test render looks blank ({ink} dark pixels).")


def setup(verify: bool = True) -> str:
    """Install the shared style. Returns the resolved font family name."""
    name, path = resolve_thai_font()
    fm.fontManager.addfont(str(path))

    mpl.rcParams.update({
        "font.family": [name, _FALLBACK_FAMILY],
        "font.size": 13,
        "axes.unicode_minus": False,   # some Thai fonts lack U+2212
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "axes.edgecolor": PALETTE["muted"],
        "axes.labelcolor": PALETTE["ink"],
        "axes.titlecolor": PALETTE["ink"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 0.8,
        "text.color": PALETTE["ink"],
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.frameon": False,
        "legend.fontsize": 11,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.dpi": 150,
        "figure.autolayout": False,
    })
    if verify:
        # Verify the composed stack, not the Thai font alone — the fallback is
        # part of the contract now.
        verify_thai_rendering()
    return name


def save(fig: plt.Figure, name: str, outdir: Path = FIGDIR) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{name}.png"
    fig.savefig(path)
    return path


# --- shared data prep ----------------------------------------------------

def valid(df: pd.DataFrame) -> pd.DataFrame:
    """Rows usable for score analysis. `passed > 0`, never `min_score > 0`."""
    return df[df["passed"] > 0]


def _national_median(df: pd.DataFrame) -> pd.Series:
    return valid(df).groupby("year")["min_score"].median()


def _year_axis(ax: plt.Axes) -> None:
    ax.set_xticks(list(YEARS))
    ax.set_xticklabels([f"{y}" for y in YEARS])
    ax.set_xlim(65.7, 69.3)


def _faculty_order(df: pd.DataFrame) -> list[str]:
    """Faculties sorted by 66->69 median-min move, biggest fall first."""
    v = valid(chula(df))
    med = v.pivot_table(index="faculty", columns="year", values="min_score",
                        aggfunc="median")
    return list((med[69] - med[66]).sort_values().index)


# --- figure 1 / 2 --------------------------------------------------------

def _draw_faculty_grid(
    subfig, df: pd.DataFrame, metric: str, order: list[str], title: str, subtitle: str
) -> None:
    ch = valid(chula(df))
    grid = subfig.subplots(4, 4, sharex=True,
                           gridspec_kw={"hspace": 0.62, "wspace": 0.22})
    axes = grid.ravel()

    if metric == "min_score":
        nat = _national_median(df)
        ylim = (0, 100)
    else:
        nat = pd.Series({y: 50.0 for y in YEARS})
        ylim = (0, 100)

    for ax, faculty in zip(axes, order):
        g = ch[ch["faculty"] == faculty]
        med_min = g.groupby("year")[metric].median()

        ax.plot(nat.index, nat.values, color=PALETTE["national"], lw=6,
                alpha=0.28, solid_capstyle="round", zorder=1)
        if metric == "min_score":
            med_max = g.groupby("year")["max_score"].median()
            ax.plot(med_max.index, med_max.values, color=PALETTE["max"], lw=1.6,
                    marker="o", ms=3.5, zorder=3, label="สูงสุด")
        ax.plot(med_min.index, med_min.values, color=PALETTE["min"], lw=2.2,
                marker="o", ms=4, zorder=4, label="ต่ำสุด")

        delta = med_min.get(69, np.nan) - med_min.get(66, np.nan)
        ax.set_title(faculty.replace("คณะ", "").replace("สำนักวิชา", ""),
                     size=12, pad=14)
        ax.text(0.5, 1.005, f"{delta:+.1f}", transform=ax.transAxes,
                ha="center", va="bottom", size=10.5,
                color=PALETTE["ok"] if delta > 0 else PALETTE["chula"])
        ax.set_ylim(*ylim)
        ax.set_yticks([0, 25, 50, 75, 100])
        _year_axis(ax)

    for ax in axes[len(order):]:
        ax.set_visible(False)

    # `sharex` parks the tick labels on the bottom row. 14 faculties in a 4x4
    # grid leave the last two cells empty, so those columns would lose their
    # x-axis entirely — put the labels back on the lowest visible panel.
    for col in range(grid.shape[1]):
        visible = [ax for ax in grid[:, col] if ax.get_visible()]
        if visible:
            visible[-1].tick_params(labelbottom=True)

    handles = [
        plt.Line2D([], [], color=PALETTE["min"], lw=2.2, marker="o", ms=4),
        plt.Line2D([], [], color=PALETTE["max"], lw=1.6, marker="o", ms=3.5),
        plt.Line2D([], [], color=PALETTE["national"], lw=6, alpha=0.28),
    ]
    labels = ["คะแนนต่ำสุด (median)", "คะแนนสูงสุด (median)",
              "national median" if metric == "min_score" else "national median = 50th pct"]
    if metric != "min_score":
        handles, labels = handles[::2], [labels[0].replace("คะแนนต่ำสุด", "percentile rank"), labels[2]]
    subfig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.035))
    subfig.suptitle(title, size=17, y=1.005, x=0.5)
    subfig.text(0.5, 0.972, subtitle, ha="center", size=11.5, color=PALETTE["muted"])


def fig_faculty_raw_vs_normalized(df: pd.DataFrame) -> plt.Figure:
    """R4 #1 + #2 — the raw grid, and the same grid on percentile rank beneath.

    Panels are ordered by the 66->69 move so the two blocks are directly
    comparable cell for cell. Divergence between the blocks is exam-scale
    drift, not a change in competitiveness.
    """
    df = df.assign(pct_rank=national_percentile_rank(df))
    order = _faculty_order(df)

    fig = plt.figure(figsize=(17, 20))
    top, bottom = fig.subfigures(2, 1, height_ratios=[1, 1], hspace=0.06)
    _draw_faculty_grid(
        top, df, "min_score", order,
        "Chula faculties — raw score, TCAS66–69",
        "median คะแนนต่ำสุด and คะแนนสูงสุด per faculty · grey band = national median "
        "· number above each panel = 66→69 move in points",
    )
    _draw_faculty_grid(
        bottom, df, "pct_rank", order,
        "The same faculties — percentile rank within each year's national distribution",
        "scale-free: immune to exam-difficulty drift · 50 = national median "
        "· same panel order as above",
    )
    return fig


# --- figure 3 ------------------------------------------------------------

def _strip_common_prefix(labels: pd.Series) -> pd.Series:
    """Remove the word-prefix every label shares, if it leaves them non-empty."""
    parts = [str(s).split() for s in labels.unique()]
    if len(parts) < 2:
        return labels
    shared: list[str] = []
    for words in zip(*parts):
        if len(set(words)) != 1:
            break
        shared.append(words[0])
    while shared:
        prefix = " ".join(shared) + " "
        if labels.str.startswith(prefix).all() and (
            labels.str.slice(len(prefix)).str.strip().str.len() > 0
        ).all():
            return labels.str.slice(len(prefix)).str.strip()
        shared.pop()
    return labels


def plot_faculty(name: str, df: pd.DataFrame) -> plt.Figure:
    """R4 #3 — every program inside one faculty, min score over time.

    Each line is one (program × major) row-group. Programs with no admits in a
    year are simply absent for that year rather than plotted at zero.
    """
    ch = valid(chula(df))
    g = ch[ch["faculty"] == name].copy()
    if g.empty:
        raise ValueError(f"no valid rows for faculty {name!r}")

    g["label"] = g["major"].where(g["major"].str.len() > 0, g["program"])
    g["label"] = g["label"].str.replace("หลักสูตร", "", regex=False).str.strip()

    # Distinct codes can still share a label (regular vs international intake).
    # Disambiguate with `detail` rather than letting two lines look identical.
    per_label_codes = g.groupby("label")["code"].nunique()
    ambiguous = set(per_label_codes[per_label_codes > 1].index)
    if ambiguous:
        extra = g["detail"].str.replace("หลักสูตร", "", regex=False).str.strip()
        needs = g["label"].isin(ambiguous) & (extra.str.len() > 0)
        g.loc[needs, "label"] = g.loc[needs, "label"] + " · " + extra[needs]

    series = {
        label: sub.groupby("year")["min_score"].median()
        for label, sub in g.groupby("label")
        if sub["year"].nunique() >= 2
    }

    # Programs in one faculty share a long degree prefix
    # ("วิศวกรรมศาสตรบัณฑิต สาขาวิชา…") that pushes the distinguishing part off
    # the end of the label. Strip it across the plotted set only — a dropped
    # single-year program must not decide the prefix for everyone else.
    trimmed = _strip_common_prefix(pd.Series(list(series)))
    series = dict(zip(trimmed, series.values()))
    order = sorted(series, key=lambda k: -series[k].iloc[-1])

    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(16, max(5.5, 0.34 * len(order) + 3.2)),
        gridspec_kw={"width_ratios": [3, 2], "wspace": 0.18},
    )

    # Sequential by rank, so neighbouring lines in the table are neighbouring
    # hues — turbo's green/red jumps read as categories that don't exist.
    cmap = plt.get_cmap("viridis")
    colors = {k: cmap(0.08 + 0.82 * (i / max(1, len(order) - 1)))
              for i, k in enumerate(order)}

    nat = _national_median(df)
    ax.plot(nat.index, nat.values, color=PALETTE["national"], lw=6, alpha=0.3,
            zorder=1, label="national median")
    for label in order:
        s = series[label]
        ax.plot(s.index, s.values, lw=2, marker="o", ms=4.5,
                color=colors[label], zorder=3)

    ax.set_title(f"{name} — คะแนนต่ำสุด by program, TCAS66–69", size=15)
    ax.set_ylabel("คะแนนต่ำสุด")
    _year_axis(ax)
    ax.legend(loc="lower left", fontsize=10)

    # Right panel: a readable legend as a ranked 66->69 change table.
    ax2.axis("off")
    ax2.set_title("66 → 69 move", size=13, loc="left")
    # Pack rows from the top at a fixed pitch. Distributing them across the
    # full axis height strands three programs in a mostly empty column.
    pitch = min(0.058, 0.94 / max(len(order), 1))
    for i, label in enumerate(order):
        s = series[label]
        y = 0.95 - i * pitch
        delta = s.iloc[-1] - s.iloc[0]
        ax2.plot([0.0, 0.05], [y, y], color=colors[label], lw=2.6,
                 transform=ax2.transAxes, clip_on=False)
        ax2.text(0.075, y, label[:52], transform=ax2.transAxes,
                 va="center", size=10.5)
        ax2.text(1.0, y, f"{delta:+.1f}", transform=ax2.transAxes,
                 va="center", ha="right", size=10.5,
                 color=PALETTE["ok"] if delta > 0 else PALETTE["chula"])
    return fig


# --- figure 4 ------------------------------------------------------------

def fig_min_max_spread(df: pd.DataFrame) -> plt.Figure:
    """R4 #4 — max minus min per program. Narrowing = the cohort is bunching."""
    ch = valid(chula(df)).copy()
    ch["spread"] = ch["max_score"] - ch["min_score"]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(15, 6.2), width_ratios=[1.15, 1])

    for code, g in ch.groupby("code"):
        s = g.groupby("year")["spread"].median()
        if len(s) >= 2:
            ax.plot(s.index, s.values, color=PALETTE["national"], lw=0.9,
                    alpha=0.30, zorder=1)
    med = ch.groupby("year")["spread"].median()
    ax.plot(med.index, med.values, color=PALETTE["chula"], lw=3.2, marker="o",
            ms=7, zorder=4, label="median across programs")
    for y, v in med.items():
        ax.annotate(f"{v:.1f}", (y, v), textcoords="offset points",
                    xytext=(0, 11), ha="center", size=11,
                    color=PALETTE["chula"])

    ax.set_title("Min–max spread per Chula program", size=15)
    ax.set_ylabel("คะแนนสูงสุด − คะแนนต่ำสุด")
    ax.legend(loc="upper right")
    _year_axis(ax)

    parts = [ch[ch["year"] == y]["spread"].dropna().values for y in YEARS]
    vp = ax2.violinplot(parts, positions=list(YEARS), widths=0.72,
                        showmedians=True, showextrema=False)
    for body in vp["bodies"]:
        body.set_facecolor(PALETTE["chula_soft"])
        body.set_alpha(0.55)
    vp["cmedians"].set_color(PALETTE["chula"])
    vp["cmedians"].set_linewidth(2)
    ax2.set_title("Distribution of the spread", size=15)
    ax2.set_ylabel("คะแนนสูงสุด − คะแนนต่ำสุด")
    _year_axis(ax2)

    fig.suptitle(
        "A narrowing spread means admitted cohorts are bunching together",
        size=12, color=PALETTE["muted"], y=0.005,
    )
    return fig


# --- figure 5 ------------------------------------------------------------

def fig_competition(df: pd.DataFrame) -> plt.Figure:
    """R4 #5 — applications, admits, applications-per-admit. The headline.

    Seats are deliberately absent (Trap 1) and the axis says *applications*,
    not applicants: one student holds up to 10 choices and can appear in up to
    10 rows, so this file cannot count people.
    """
    peers = df[df["univ"].isin(PEERS)].copy()
    agg = peers.groupby(["univ", "year"]).agg(
        applied=("applied", "sum"), passed=("passed", "sum")
    ).reset_index()
    agg["per_admit"] = agg["applied"] / agg["passed"]

    fig, axes = plt.subplots(1, 3, figsize=(17.5, 6.0))
    specs = [
        ("applied", "Applications (สมัคร)", "applications, thousands", 1e-3),
        ("passed", "Admits (ผ่าน)", "admits", 1.0),
        ("per_admit", "Applications per admit", "applications ÷ admits", 1.0),
    ]

    for ax, (col, title, ylabel, scale) in zip(axes, specs):
        for i, (univ, label) in enumerate(PEERS.items()):
            g = agg[agg["univ"] == univ].sort_values("year")
            is_chula = univ == CHULA
            ax.plot(
                g["year"], g[col] * scale,
                color=PALETTE["chula"] if is_chula else PEER_COLORS[i % len(PEER_COLORS)],
                lw=3.4 if is_chula else 1.5,
                marker="o", ms=6 if is_chula else 3.5,
                alpha=1.0 if is_chula else 0.62,
                zorder=5 if is_chula else 2,
                label=label,
            )
        ax.set_title(title, size=14)
        ax.set_ylabel(ylabel)
        _year_axis(ax)

    ch = agg[agg["univ"] == CHULA].set_index("year")
    drop = 1 - ch.loc[69, "applied"] / ch.loc[66, "applied"]
    # Offsets in points, anchored to the Chula line's own endpoint, so the
    # labels cannot drift into a peer line the way absolute coordinates did.
    axes[0].annotate(
        f"Chula {drop:.0%}",
        xy=(69, ch.loc[69, "applied"] / 1e3),
        textcoords="offset points", xytext=(-8, -22), ha="right",
        color=PALETTE["chula"], size=12.5, weight="bold",
    )
    axes[2].annotate(
        f"{ch.loc[66, 'per_admit']:.1f} → {ch.loc[69, 'per_admit']:.1f}",
        xy=(66, ch.loc[66, "per_admit"]),
        textcoords="offset points", xytext=(6, 12), ha="left",
        color=PALETTE["chula"], size=12.5, weight="bold",
    )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=9, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Competition, TCAS66–69 — Chula vs peers", size=17, y=1.02)
    fig.text(
        0.5, 0.955,
        "counts are applications, not applicants — one student holds up to 10 "
        "choices · seats (รับ) are omitted: the file cannot reconcile them",
        ha="center", size=11.5, color=PALETTE["muted"],
    )
    return fig


# --- figure 6 ------------------------------------------------------------

def fig_peer_comparison(df: pd.DataFrame) -> plt.Figure:
    """R4 #6 — median min score by university, T-Score scorers marked.

    KMITL, Chiang Mai, Thammasat and Silpakorn publish T-Score-weighted
    composites; Chula and the rest publish raw-weighted percent. A T-Score 60
    and a raw 60 are not the same achievement, so those series are drawn
    dashed and called out — plotting them as comparable levels would be wrong.
    """
    peers = valid(df[df["univ"].isin(PEERS)])
    med = peers.groupby(["univ", "year"])["min_score"].median().reset_index()

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(16.5, 6.4), width_ratios=[1.25, 1])

    for i, (univ, label) in enumerate(PEERS.items()):
        g = med[med["univ"] == univ].sort_values("year")
        is_chula = univ == CHULA
        is_tscore = univ in TSCORE_UNIVERSITIES
        ax.plot(
            g["year"], g["min_score"],
            color=PALETTE["chula"] if is_chula else PEER_COLORS[i % len(PEER_COLORS)],
            lw=3.4 if is_chula else 1.8,
            ls="--" if is_tscore else "-",
            marker="s" if is_tscore else "o",
            ms=6 if is_chula else 4,
            alpha=1.0 if is_chula else 0.72,
            zorder=5 if is_chula else 2,
            label=f"{label}{'  (T-Score)' if is_tscore else ''}",
        )
    ax.set_title("Median คะแนนต่ำสุด by university", size=15)
    ax.set_ylabel("median คะแนนต่ำสุด (passed > 0)")
    _year_axis(ax)
    # Figure-level legend along the bottom: anchoring it to the axes pushed it
    # straight over the explanation panel on the right.
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, -0.10), fontsize=11)

    # Right: the scale warning, made concrete.
    ax2.axis("off")
    ax2.text(0, 1.0, "Why these lines are not comparable", size=14,
             va="top", weight="bold")
    ax2.text(
        0, 0.87,
        "The composite is  Σ (raw_subject ÷ 100) × weight,  weights summing\n"
        "to 100 — so most universities publish a 0–100 raw-weighted score.\n\n"
        "But KMITL, Chiang Mai, Thammasat and Silpakorn specify T-Score in\n"
        "their เกณฑ์, so their published numbers are T-Score-weighted:\n\n"
        "        T = 50 + c · (X − mean) / SD\n\n"
        "and c is re-derived every year from the most extreme single score\n"
        "in the whole cohort. A T-Score 60 in TCAS66 and in TCAS69 are not\n"
        "the same achievement, let alone the same as a raw 60.\n\n"
        "Dashed + square markers = T-Score scale. Compare their shape over\n"
        "time, never their level against Chula's.",
        size=11.7, va="top", linespacing=1.55, color=PALETTE["ink"],
    )
    return fig


# --- figure 7 ------------------------------------------------------------

def fig_exam_difficulty(exam_stats: pd.DataFrame | None = None) -> plt.Figure:
    """R4 #7 — the "why raw scores lie" exhibit.

    Subject means and SDs by year, the published T-Score coefficient, and the
    single subject that pinned it.
    """
    stats = exam_stats if exam_stats is not None else load_exam_stats()
    coeffs = load_coefficients()
    drivers = tscore_drivers(stats, coeffs)
    difficulty = cohort_difficulty_index(stats)

    fig, axes = plt.subplots(2, 2, figsize=(16.5, 11))
    (ax_mean, ax_sd), (ax_coef, ax_drive) = axes

    for ax, col, title, ylabel in [
        (ax_mean, "mean", "Subject means by year", "mean score"),
        (ax_sd, "sd", "Subject SDs by year", "standard deviation"),
    ]:
        for family, marker in [("A-Level", "o"), ("TGAT/TPAT", "s")]:
            fam = stats[stats["exam_family"] == family]
            for subject, g in fam.groupby("subject_en"):
                g = g.sort_values("tcas_year")
                ax.plot(g["tcas_year"], g[col], lw=1.0, alpha=0.42,
                        marker=marker, ms=3,
                        color=PALETTE["max"] if family == "A-Level" else PALETTE["accent"])
        for family, color in [("A-Level", PALETTE["max"]), ("TGAT/TPAT", PALETTE["accent"])]:
            d = difficulty[difficulty["exam_family"] == family].sort_values("tcas_year")
            key = "mean_index" if col == "mean" else "sd_index"
            ax.plot(d["tcas_year"], d[key], lw=3.4, color=color, marker="o", ms=7,
                    label=f"{family} (examinee-weighted)", zorder=5)
        ax.set_title(title, size=14)
        ax.set_ylabel(ylabel)
        ax.legend(loc="best", fontsize=10.5)
        _year_axis(ax)

    # Highlight the two subjects the spec calls out.
    for subject, note in [("Chem", "เคมี mean"), ("Phy", "ฟิสิกส์ SD")]:
        g = stats[(stats["subject_en"] == subject)].sort_values("tcas_year")
        target_ax, col = (ax_mean, "mean") if subject == "Chem" else (ax_sd, "sd")
        target_ax.plot(g["tcas_year"], g[col], lw=2.6, color=PALETTE["chula"],
                       marker="D", ms=6, zorder=6)
        target_ax.annotate(
            f"{note}: " + " → ".join(f"{v:.2f}" for v in g[col]),
            xy=(66.05, g[col].iloc[0]), xytext=(66.05, g[col].iloc[0] + 6),
            size=11, color=PALETTE["chula"],
        )

    for family, color in [("A-Level", PALETTE["max"]), ("TGAT/TPAT", PALETTE["accent"])]:
        d = drivers[drivers["exam_family"] == family].sort_values("tcas_year")
        ax_coef.plot(d["tcas_year"], d["published_c"], lw=3, marker="o", ms=8,
                     color=color, label=family)
        for _, r in d.iterrows():
            ax_coef.annotate(f"{r['published_c']:.3f}", (r["tcas_year"], r["published_c"]),
                             textcoords="offset points", xytext=(0, 11), ha="center",
                             size=10.5, color=color)
    ax_coef.set_title("Published T-Score coefficient c", size=14)
    ax_coef.set_ylabel("c")
    ax_coef.legend(fontsize=10.5)
    _year_axis(ax_coef)

    ax_drive.axis("off")
    ax_drive.text(0, 1.0, "c is exactly  50 / max|z|", size=15, va="top", weight="bold")
    ax_drive.text(
        0, 0.905,
        "where the max runs over every subject in that family that year —\n"
        "so one candidate's score sets the scale for the whole cohort.",
        size=11.7, va="top", color=PALETTE["muted"], linespacing=1.5,
    )
    header = f"{'family':<11}{'yr':<5}{'published':<11}{'implied':<10}{'err':<9}driver"
    ax_drive.text(0, 0.78, header, size=11, va="top", family="monospace",
                  color=PALETTE["muted"])
    for i, (_, r) in enumerate(drivers.iterrows()):
        ax_drive.text(
            0, 0.735 - i * 0.062,
            f"{r['exam_family']:<11}{r['tcas_year']:<5}{r['published_c']:<11.5f}"
            f"{r['implied_c']:<10.5f}{r['rel_error']:<9.4%}"
            f"{r['driver']} ({r['side']}={r['driver_value']:g})",
            size=11, va="top", family="monospace",
        )
    ax_drive.text(
        0, 0.20,
        "In every year the TGAT/TPAT scale is pinned by TPAT5's *minimum* —\n"
        "a single candidate. A T-Score of 60 is therefore not the same\n"
        "achievement in TCAS66 and TCAS69, and any university scoring in\n"
        "T-Score has a scale break at every year boundary.",
        size=11.7, va="top", linespacing=1.55,
    )
    fig.suptitle("Why raw scores lie: the papers move, and so does the scale",
                 size=17, y=0.985)
    return fig


# --- figure 8 ------------------------------------------------------------

def fig_ds_effect(df: pd.DataFrame) -> plt.Figure:
    """R4 #8 — what Double Sorting does to the floor, TCAS67–69.

    Note the spec's claim that ``min_ds <= min`` always is false: 333/337/352
    national rows a year move *up*. When marginal admits decline their seat the
    remaining floor can rise, and a program that admitted nobody in the first
    pass jumps from a zero floor to a real one.
    """
    d = df.dropna(subset=["min_score", "min_score_ds"]).copy()
    d = d[d["passed"] > 0]
    d["drop"] = d["min_score"] - d["min_score_ds"]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(16, 6.2), width_ratios=[1.3, 1])

    lo, hi = -8, 22
    bins = np.linspace(lo, hi, 61)
    for i, year in enumerate((67, 68, 69)):
        g = d[d["year"] == year]["drop"]
        ax.hist(g.clip(lo, hi), bins=bins, histtype="step", lw=2.2,
                color=PEER_COLORS[i + 1], label=f"TCAS{year}  (median {g.median():.2f})")
    ax.axvline(0, color=PALETTE["ink"], lw=1.2, ls=":")
    # Log y: roughly 2 rows in 5 are unchanged by DS, and on a linear axis that
    # single spike flattens the entire tail that the chart is about.
    ax.set_yscale("log")
    ax.set_xlabel("คะแนนต่ำสุด − คะแนนต่ำสุด (DS)   →  how far Double Sorting lowered the floor")
    ax.set_ylabel("rows (log scale)")
    ax.set_title("Double Sorting lowers the floor — usually", size=15)
    ax.legend(fontsize=11, loc="upper right")
    ax.annotate("floor rose\nafter DS", xy=(-5.0, ax.get_ylim()[1] * 0.06),
                size=11, color=PALETTE["muted"], ha="center")
    ax.annotate("unchanged", xy=(0.35, ax.get_ylim()[1] * 0.5),
                size=11, color=PALETTE["muted"], ha="left")

    # The end bins are overflow, not modes — say so, or they read as real peaks.
    below, above = (d["drop"] < lo).mean() * 100, (d["drop"] > hi).mean() * 100
    ax.set_xticks([lo, -5, 0, 5, 10, 15, 20, hi])
    ax.set_xticklabels([f"≤{lo}", "-5", "0", "5", "10", "15", "20", f"≥{hi}"])
    ax.text(
        0.5, -0.20,
        f"end bins are overflow: {below:.1f}% of rows below {lo}, {above:.1f}% above {hi} "
        f"(full range {d['drop'].min():.1f} to {d['drop'].max():.1f})",
        transform=ax.transAxes, ha="center", size=10.5, color=PALETTE["muted"],
    )

    summary = []
    for year in (67, 68, 69):
        g = d[d["year"] == year]
        summary.append({
            "year": year,
            "median drop": g["drop"].median(),
            "mean drop": g["drop"].mean(),
            "% lowered": (g["drop"] > 1e-9).mean() * 100,
            "% unchanged": (g["drop"].abs() <= 1e-9).mean() * 100,
            "% raised": (g["drop"] < -1e-9).mean() * 100,
        })
    s = pd.DataFrame(summary).set_index("year")

    x = np.arange(len(s))
    cats = [("% lowered", -0.27, PALETTE["max"]),
            ("% unchanged", 0.0, PALETTE["national"]),
            ("% raised", 0.27, PALETTE["accent"])]
    for col, offset, color in cats:
        ax2.bar(x + offset, s[col], width=0.26, color=color, label=col.replace("% ", "floor "))
        for i, v in enumerate(s[col]):
            ax2.text(i + offset, v + 1.5, f"{v:.0f}%", ha="center", size=10.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"TCAS{y}" for y in s.index])
    ax2.set_ylabel("% of rows with admits")
    ax2.set_ylim(0, 100)
    ax2.set_title("Direction of the DS move", size=15)
    ax2.legend(fontsize=11)

    fig.suptitle(
        "TCAS66 is absent: ทปอ. ran Double Sorting that year but never published it",
        size=11.5, color=PALETTE["muted"], y=0.005,
    )
    return fig
