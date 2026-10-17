"""Checks for Lorenz and Pen plots against the coordinates from ineq 0.2-13."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

from ineq.lorenz import Lc
from ineq.plots import Pen, lines_lc, lines_theor_lc, plot_lc, plot_theor_lc
from ineq.theor import lc_dagum, lc_lognorm, theorLc

TOLERANCE = 1e-8
USA_X = np.array(
    [541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261],
    dtype=np.float64,
)
USA_N = np.array(
    [482, 825, 722, 690, 661, 760, 745, 2140, 1911, 1024],
    dtype=np.float64,
)
GRID = np.arange(1001, dtype=np.float64) * 0.001


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def test_plot_lc_returns_ordinary_and_generalized_ordinates():
    curve = Lc(USA_X, n=USA_N)
    fig, ax = plt.subplots()
    ordinary = plot_lc(curve, ax=ax)
    assert ordinary["p"] == pytest.approx(curve["p"], abs=TOLERANCE)
    assert ordinary["y"] == pytest.approx(curve["L"], abs=TOLERANCE)
    assert len(ax.lines) == 2
    diagonal = ax.lines[1].get_xydata()
    assert diagonal[:, 0] == pytest.approx([0.0, 1.0], abs=TOLERANCE)
    assert diagonal[:, 1] == pytest.approx([0.0, curve["L"][-1]], abs=TOLERANCE)
    assert ax.get_title() == "Lorenz curve"
    assert ax.get_xlim() == pytest.approx((0.0, 1.0), abs=TOLERANCE)

    fig, ax = plt.subplots()
    generalized = plot_lc(curve, general=True, ax=ax, main="Generalized")
    assert generalized["y"] == pytest.approx(curve["L.general"], abs=TOLERANCE)
    assert ax.lines[1].get_ydata() == pytest.approx(
        [0.0, curve["L.general"][-1]], abs=TOLERANCE
    )
    assert ax.get_title() == "Generalized"


def test_lines_lc_adds_the_curve_without_a_diagonal():
    curve = Lc(USA_X, n=USA_N)
    fig, ax = plt.subplots()
    added = lines_lc(curve, ax=ax, color="C1", linewidth=3)
    assert added["p"] == pytest.approx(curve["p"], abs=TOLERANCE)
    assert added["y"] == pytest.approx(curve["L"], abs=TOLERANCE)
    assert len(ax.lines) == 1
    assert ax.lines[0].get_linewidth() == 3

    generalized = lines_lc(curve, general=True, ax=ax)
    assert generalized["y"] == pytest.approx(curve["L.general"], abs=TOLERANCE)
    assert len(ax.lines) == 2
    assert ax.lines[1].get_color() == "black"


def test_theor_plots_use_the_thousandth_grid_and_the_parameter_rule():
    fig, ax = plt.subplots()
    drawn = plot_theor_lc(lc_lognorm, parameter=0.78, ax=ax)
    expected = lc_lognorm(GRID, parameter=0.78)
    assert drawn["p"] == pytest.approx(GRID, abs=0.0)
    assert drawn["y"] == pytest.approx(expected, abs=TOLERANCE)
    assert len(ax.lines) == 2
    assert ax.lines[1].get_xydata()[:, 1] == pytest.approx([0.0, 1.0], abs=TOLERANCE)
    assert drawn["p"].shape == (1001,)

    seen = {}

    def baked(p):
        seen["n"] = len(p)
        return np.zeros(len(p))

    fig, ax = plt.subplots()
    blank = plot_theor_lc(baked, ax=ax)
    assert seen["n"] == 1001
    assert blank["y"] == pytest.approx(np.zeros(1001), abs=TOLERANCE)

    fixed = theorLc("lognorm", parameter=0.78)
    overlay = lines_theor_lc(fixed, ax=ax)
    assert overlay["y"] == pytest.approx(expected, abs=TOLERANCE)
    assert ax.lines[-1].get_color() == "C1"
    assert ax.lines[-1].get_linewidth() == 2


def test_pen_orders_scales_and_builds_cumulative_shares():
    fig, ax = plt.subplots()
    scaled = Pen(USA_X, n=USA_N, ax=ax)
    ordered = np.sort(USA_X, kind="mergesort")
    weights = USA_N[np.argsort(USA_X, kind="mergesort")]
    heights = ordered / np.mean(ordered)
    shares = np.cumsum(np.concatenate(([0.0], weights))) / np.sum(weights)
    assert scaled["y"] == pytest.approx(heights, abs=TOLERANCE)
    assert scaled["p"] == pytest.approx(shares, abs=TOLERANCE)
    assert scaled["p"][0] == 0.0
    assert scaled["p"][-1] == pytest.approx(1.0, abs=TOLERANCE)
    assert scaled["mean"] == pytest.approx(float(np.mean(heights)), abs=TOLERANCE)
    assert len(ax.lines) == 2
    assert ax.get_title() == "Pen's Parade"

    fig, ax = plt.subplots()
    raw = Pen(USA_X, n=USA_N, scaled=False, ax=ax)
    assert raw["y"] == pytest.approx(ordered, abs=TOLERANCE)
    assert raw["p"] == pytest.approx(shares, abs=TOLERANCE)
    assert raw["mean"] == pytest.approx(float(np.mean(ordered)), abs=TOLERANCE)


def test_pen_drops_missing_values_and_keeps_ties_in_input_order():
    fig, ax = plt.subplots()
    parade = Pen(
        np.array([3.0, np.nan, 1.0, 1.0]),
        n=np.array([10.0, 99.0, 30.0, 40.0]),
        scaled=False,
        ax=ax,
    )
    assert parade["y"] == pytest.approx([1.0, 1.0, 3.0], abs=TOLERANCE)
    assert parade["p"] == pytest.approx([0.0, 30.0 / 80.0, 70.0 / 80.0, 1.0], abs=TOLERANCE)
    assert parade["mean"] == pytest.approx(5.0 / 3.0, abs=TOLERANCE)


def test_pen_groups_draw_bars_and_leave_the_coordinates_unchanged():
    fig, ax = plt.subplots()
    plain = Pen(USA_X, n=USA_N, segments=False, ax=ax)
    fig, ax = plt.subplots()
    grouped = Pen(
        USA_X,
        n=USA_N,
        group=[1, 1, 1, 2, 2, 2, 3, 3, 3, 3],
        ax=ax,
    )
    assert grouped["y"] == pytest.approx(plain["y"], abs=TOLERANCE)
    assert grouped["p"] == pytest.approx(plain["p"], abs=TOLERANCE)
    assert grouped["mean"] == pytest.approx(plain["mean"], abs=TOLERANCE)
    assert len(ax.containers) == 1
    assert len(ax.containers[0]) == 10
    assert ax.get_xlim() == pytest.approx((0.0, 1.0), abs=TOLERANCE)
    assert ax.get_ylim()[0] == pytest.approx(0.0, abs=TOLERANCE)

    fig, ax = plt.subplots()
    Pen(USA_X, n=USA_N, ax=ax)
    before = len(ax.lines)
    Pen(USA_X, n=USA_N, add=True, abline=True, ax=ax)
    assert len(ax.lines) == before + 1


def test_plot_coordinates_match_installed_ineq():
    reference = _r_reference()
    if reference is None:
        pytest.skip("Rscript or ineq is unavailable")

    curve = Lc(USA_X, n=USA_N)
    fig, ax = plt.subplots()
    ordinary = plot_lc(curve, ax=ax)
    generalized = plot_lc(curve, general=True, ax=ax)
    lines_ordinary = lines_lc(curve, ax=ax)
    lines_general = lines_lc(curve, general=True, ax=ax)
    for drawn, key in (
        (ordinary, "L"),
        (lines_ordinary, "L"),
        (generalized, "L.general"),
        (lines_general, "L.general"),
    ):
        assert drawn["p"] == pytest.approx(reference["p"], abs=TOLERANCE)
        assert drawn["y"] == pytest.approx(reference[key], abs=TOLERANCE)

    fig, ax = plt.subplots()
    theor = plot_theor_lc(lc_lognorm, parameter=0.78, ax=ax)
    theor_line = lines_theor_lc(lc_lognorm, parameter=0.78, ax=ax)
    assert theor["p"] == pytest.approx(reference["grid"], abs=TOLERANCE)
    assert theor["y"] == pytest.approx(reference["lognorm"], abs=TOLERANCE)
    assert theor_line["y"] == pytest.approx(reference["lognorm"], abs=TOLERANCE)

    fig, ax = plt.subplots()
    scaled = Pen(USA_X, n=USA_N, ax=ax)
    raw = Pen(USA_X, n=USA_N, scaled=False, ax=ax)
    assert scaled["y"] == pytest.approx(reference["pen_scaled_y"], abs=TOLERANCE)
    assert scaled["p"] == pytest.approx(reference["pen_p"], abs=TOLERANCE)
    assert scaled["mean"] == pytest.approx(reference["pen_scaled_mean"], abs=TOLERANCE)
    assert raw["y"] == pytest.approx(reference["pen_raw_y"], abs=TOLERANCE)
    assert raw["p"] == pytest.approx(reference["pen_p"], abs=TOLERANCE)
    assert raw["mean"] == pytest.approx(reference["pen_raw_mean"], abs=TOLERANCE)


def _r_reference():
    if shutil.which("Rscript") is None:
        return None
    script = textwrap.dedent(
        """
        if (!requireNamespace("ineq", quietly=TRUE)) quit(status=2)
        x <- c(541, 1463, 2445, 3438, 4437, 5401, 6392, 8304, 11904, 22261)
        n <- c(482, 825, 722, 690, 661, 760, 745, 2140, 1911, 1024)
        curve <- ineq::Lc(x, n=n)
        grid <- (0:1000) * 0.001
        emit <- function(name, v) {
          cat("## ", name, "\\n", sep="")
          cat(sprintf("%.17g\\n", v), sep="")
        }
        emit("p", curve$p)
        emit("L", curve$L)
        emit("L.general", curve$L.general)
        emit("grid", grid)
        emit("lognorm", ineq::Lc.lognorm(grid, parameter=0.78))
        pen <- function(scaled) {
          ina <- !is.na(x)
          nn <- n[ina]
          xx <- as.numeric(x)[ina]
          o <- order(xx)
          xx <- xx[o]
          nn <- nn[o]
          if (scaled) xx <- xx / mean(xx)
          shares <- cumsum(c(0, nn)) / sum(nn)
          list(y=xx, p=shares, mean=mean(xx))
        }
        scaled <- pen(TRUE)
        raw <- pen(FALSE)
        emit("pen_scaled_y", scaled$y)
        emit("pen_raw_y", raw$y)
        emit("pen_p", scaled$p)
        emit("pen_scaled_mean", scaled$mean)
        emit("pen_raw_mean", raw$mean)
        """
    )
    with tempfile.TemporaryDirectory() as directory:
        program = Path(directory) / "check.R"
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program)],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return _parse_blocks(result.stdout)


def _parse_blocks(text):
    blocks = {}
    name = None
    rows = []
    for line in text.splitlines():
        if line.startswith("## "):
            if name is not None:
                blocks[name] = _floats(rows)
            name = line[3:]
            rows = []
        elif line.strip():
            rows.append(line.strip())
    if name is not None:
        blocks[name] = _floats(rows)
    return blocks


def _floats(rows):
    values = []
    for token in rows:
        if token in {"NaN", "NA", "nan"}:
            values.append(np.nan)
        else:
            values.append(float(token))
    return np.asarray(values, dtype=np.float64)
