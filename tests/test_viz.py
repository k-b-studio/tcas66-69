"""Tests for the figure layer — mostly: do Thai glyphs actually render.

R4's acceptance criterion is that the charts show Thai, not tofu boxes. A font
being *set* proves nothing: matplotlib silently falls back to DejaVu Sans and
draws a box per glyph. These tests exercise the real detection path.
"""

from __future__ import annotations

import warnings

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.load import load_all  # noqa: E402
from src import viz  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def style() -> str:
    return viz.setup()


@pytest.fixture(scope="module")
def df():
    return load_all()


def test_resolved_font_actually_covers_thai() -> None:
    name, path = viz.resolve_thai_font()
    assert viz._covers_thai(path), f"{name} does not cover the Thai probe"


def test_named_font_is_not_trusted_blindly() -> None:
    """`Sarabun` is listed by the font manager here but resolves to DejaVu.

    This is the exact failure mode the resolver exists to prevent, so the
    resolver must never hand back a font whose file lacks Thai.
    """
    _, path = viz.resolve_thai_font()
    assert "DejaVu" not in path.name


def test_verifier_rejects_a_font_without_thai() -> None:
    """The tofu detector must fail on tofu, or it is worthless."""
    with pytest.raises(RuntimeError, match="tofu"):
        viz.verify_thai_rendering("DejaVu Sans")


def test_verifier_accepts_the_configured_stack() -> None:
    viz.verify_thai_rendering()


@pytest.mark.parametrize(
    "figure",
    ["competition", "peer", "spread", "ds", "exam", "faculty_grid", "plot_faculty"],
)
def test_figures_render_without_missing_glyphs(df, figure: str) -> None:
    """Every figure, drawn for real, must emit no missing-glyph warning."""
    builders = {
        "competition": lambda: viz.fig_competition(df),
        "peer": lambda: viz.fig_peer_comparison(df),
        "spread": lambda: viz.fig_min_max_spread(df),
        "ds": lambda: viz.fig_ds_effect(df),
        "exam": lambda: viz.fig_exam_difficulty(),
        "faculty_grid": lambda: viz.fig_faculty_raw_vs_normalized(df),
        "plot_faculty": lambda: viz.plot_faculty("คณะวิศวกรรมศาสตร์", df),
    }
    import io

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig = builders[figure]()
        fig.savefig(io.BytesIO(), format="png", dpi=60)
        plt.close(fig)

    missing = sorted({str(w.message) for w in caught if "missing from font" in str(w.message)})
    assert not missing, f"{figure}: {missing}"


def test_plot_faculty_rejects_unknown_faculty(df) -> None:
    with pytest.raises(ValueError):
        viz.plot_faculty("คณะไม่มีอยู่จริง", df)


def test_peer_set_resolves_exactly(df) -> None:
    """Every peer name must match a real university string, exactly once.

    `contains` matching would silently pull in ราชภัฏเชียงใหม่ and
    ราชภัฏธนบุรี, which are different institutions.
    """
    present = set(df["univ"])
    for name in viz.PEERS:
        assert name in present, f"peer not found: {name}"


def test_tscore_peers_are_marked(df) -> None:
    """At least the four T-Score universities in the peer set are flagged."""
    from src.load import TSCORE_UNIVERSITIES

    flagged = set(viz.PEERS) & TSCORE_UNIVERSITIES
    assert len(flagged) >= 4


def test_strip_common_prefix_keeps_labels_distinct() -> None:
    import pandas as pd

    labels = pd.Series([
        "วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมโยธา",
        "วิศวกรรมศาสตรบัณฑิต สาขาวิชาวิศวกรรมสำรวจ",
    ])
    out = viz._strip_common_prefix(labels)
    assert out.nunique() == 2
    assert not out.str.startswith("วิศวกรรมศาสตรบัณฑิต").any()
    assert (out.str.len() > 0).all()


def test_strip_common_prefix_is_a_noop_when_nothing_is_shared() -> None:
    import pandas as pd

    labels = pd.Series(["การปกครอง", "รัฐประศาสนศาสตร์"])
    assert list(viz._strip_common_prefix(labels)) == list(labels)
