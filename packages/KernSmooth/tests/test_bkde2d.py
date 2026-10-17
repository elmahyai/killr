"""Checks for lbtwod and bkde2d, including a comparison with R on the geyser data."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from kernsmooth.bkde2d import bkde2d
from lbtwod import lbtwod


def test_lbtwod_splits_an_interior_point():
    counts = lbtwod(np.array([0.1]), np.array([0.1]), 0.0, 0.0, 1.0, 1.0, 5, 5)
    grid = counts.reshape(5, 5)
    assert grid[0, 0] == pytest.approx(0.36)
    assert grid[1, 0] == pytest.approx(0.24)
    assert grid[0, 1] == pytest.approx(0.24)
    assert grid[1, 1] == pytest.approx(0.16)
    assert grid.sum() == pytest.approx(1.0)


def test_lbtwod_ignores_the_exact_upper_edge_and_outside_points():
    upper = lbtwod(np.array([1.0, 0.25]), np.array([0.25, 1.0]), 0.0, 0.0, 1.0, 1.0, 3, 3)
    outside = lbtwod(np.array([-0.2]), np.array([0.4]), 0.0, 0.0, 1.0, 1.0, 4, 4)
    assert upper.tolist() == [0.0] * 9
    assert outside.tolist() == [0.0] * 16


def test_bkde2d_default_range_extends_by_one_and_a_half_bandwidths():
    from mass import geyser

    sample = np.column_stack((geyser["duration"], geyser["waiting"])).astype(np.float64)
    estimate = bkde2d(sample, bandwidth=(0.7, 7.0))
    assert estimate["x1"].shape == (51,)
    assert estimate["x2"].shape == (51,)
    assert estimate["fhat"].shape == (51, 51)
    assert np.all(np.isfinite(estimate["fhat"]))
    assert np.min(estimate["fhat"]) >= 0.0
    assert estimate["x1"][0] == pytest.approx(sample[:, 0].min() - 1.5 * 0.7)
    assert estimate["x1"][-1] == pytest.approx(sample[:, 0].max() + 1.5 * 0.7)
    assert estimate["x2"][0] == pytest.approx(sample[:, 1].min() - 1.5 * 7.0)
    assert estimate["x2"][-1] == pytest.approx(sample[:, 1].max() + 1.5 * 7.0)


def test_bkde2d_rejects_a_non_positive_bandwidth():
    sample = np.array([[0.0, 1.0], [1.0, 2.0]])
    with pytest.raises(ValueError, match="bandwidth"):
        bkde2d(sample, bandwidth=(0.7, 0.0))


def test_bkde2d_warns_when_the_grid_is_coarser_than_the_kernel():
    sample = np.array([[0.2, 0.3], [0.4, 0.6], [0.5, 0.2]])
    with pytest.warns(UserWarning, match="Binning grid too coarse"):
        bkde2d(sample, bandwidth=(1e-8, 1e-8), range_x=((0.0, 1.0), (0.0, 1.0)))


def test_lbtwod_matches_r():
    reference = _r_linbin2d()
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    counts = lbtwod(
        np.array([0.1, 1.0, -0.2]),
        np.array([0.25, 0.4, 0.5]),
        0.0,
        0.0,
        1.0,
        1.0,
        5,
        4,
    ).reshape(5, 4)
    assert counts == pytest.approx(reference, abs=1e-12)


def test_bkde2d_matches_r_on_geyser():
    from mass import geyser

    sample = np.column_stack((geyser["duration"], geyser["waiting"])).astype(np.float64)
    reference = _r_bkde2d()
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    estimate = bkde2d(sample, bandwidth=(0.7, 7.0))
    assert estimate["x1"] == pytest.approx(reference["x1"], abs=1e-8)
    assert estimate["x2"] == pytest.approx(reference["x2"], abs=1e-8)
    assert estimate["fhat"] == pytest.approx(reference["fhat"], abs=1e-8)


def _r_linbin2d():
    script = textwrap.dedent(
        """
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        x <- cbind(c(0.1, 1, -0.2), c(0.25, 0.4, 0.5))
        g1 <- seq(0, 1, length.out=5)
        g2 <- seq(0, 1, length.out=4)
        counts <- KernSmooth:::linbin2D(x, g1, g2)
        cat(sprintf("%.17g\\n", counts), sep="")
        """
    )
    values = _run_r(script)
    if values is None:
        return None
    return np.fromstring(values, sep="\n").reshape(5, 4, order="F")


def _r_bkde2d():
    script = textwrap.dedent(
        """
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        if (!requireNamespace("MASS", quietly=TRUE)) quit(status=2)
        data(geyser, package="MASS")
        x <- cbind(geyser$duration, geyser$waiting)
        est <- KernSmooth::bkde2D(x, bandwidth=c(0.7, 7))
        cat(sprintf("%.17g\\n", est$x1), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$x2), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$fhat), sep="")
        """
    )
    values = _run_r(script)
    if values is None:
        return None
    grid1, grid2, density = values.split("---")
    x1 = np.fromstring(grid1, sep="\n")
    x2 = np.fromstring(grid2, sep="\n")
    return {
        "x1": x1,
        "x2": x2,
        "fhat": np.fromstring(density, sep="\n").reshape(x1.size, x2.size, order="F"),
    }


def _run_r(script: str):
    if shutil.which("Rscript") is None:
        return None
    result = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout
