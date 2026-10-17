"""Checks for linbin and bkde, including a comparison with R when it is installed."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from kernsmooth import bkde
from linbin import linbin


def test_linbin_splits_an_interior_point():
    counts = linbin(np.array([0.1]), 0.0, 1.0, 5, True)
    assert counts.shape == (5,)
    assert counts[0] == pytest.approx(0.6)
    assert counts[1] == pytest.approx(0.4)
    assert counts[2:].tolist() == [0.0, 0.0, 0.0]


def test_linbin_truncation_drops_outside_points():
    counts = linbin(np.array([-0.2, 1.2]), 0.0, 1.0, 5, True)
    assert counts.tolist() == [0.0, 0.0, 0.0, 0.0, 0.0]


def test_linbin_keeps_outside_points_on_the_end_bins():
    counts = linbin(np.array([-0.2, 1.2]), 0.0, 1.0, 5, False)
    assert counts[0] == pytest.approx(1.0)
    assert counts[4] == pytest.approx(1.0)
    assert counts[1:4].tolist() == [0.0, 0.0, 0.0]


def test_linbin_exact_right_endpoint_follows_fortran_int():
    dropped = linbin(np.array([1.0]), 0.0, 1.0, 5, True)
    assert dropped.tolist() == [0.0, 0.0, 0.0, 0.0, 0.0]

    kept = linbin(np.array([1.0]), 0.0, 1.0, 5, False)
    assert kept[4] == pytest.approx(1.0)
    assert kept[:4].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_bkde_shape_integral_and_finite_values():
    sample = np.random.default_rng(0).normal(size=200)
    estimate = bkde(sample)
    assert estimate["x"].shape == (401,)
    assert estimate["y"].shape == (401,)
    assert np.all(np.isfinite(estimate["y"]))
    assert np.min(estimate["y"]) >= -1e-8
    integral = np.trapezoid(estimate["y"], estimate["x"])
    assert integral == pytest.approx(1.0, abs=0.05)


def test_bkde_rejects_a_non_positive_bandwidth():
    with pytest.raises(ValueError, match="bandwidth"):
        bkde(np.array([0.0, 1.0]), bandwidth=0.0)


def test_linbin_matches_r():
    reference = _r_linbin(np.array([0.1, -0.2, 1.0, 1.2]), truncate=False)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    counts = linbin(np.array([0.1, -0.2, 1.0, 1.2]), 0.0, 1.0, 5, False)
    assert counts == pytest.approx(np.fromstring(reference, sep="\n"), abs=1e-12)


def test_bkde_matches_r():
    sample = np.random.default_rng(1).normal(size=80)
    reference = _r_bkde(sample)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    estimate = bkde(sample)
    assert estimate["x"] == pytest.approx(reference["x"], abs=1e-8)
    assert estimate["y"] == pytest.approx(reference["y"], abs=1e-8)


def _r_linbin(sample: np.ndarray, truncate: bool):
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        tr <- as.logical(args[[2]])
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        counts <- KernSmooth:::linbin(x, seq(0, 1, length.out=5), tr)
        cat(counts, sep="\\n")
        """
    )
    return _run_r(script, sample, "TRUE" if truncate else "FALSE")


def _r_bkde(sample: np.ndarray):
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        est <- KernSmooth::bkde(x)
        cat(sprintf("%.17g\\n", est$x), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$y), sep="")
        """
    )
    values = _run_r(script, sample)
    if values is None:
        return None
    grid, density = values.split("---")
    return {
        "x": np.fromstring(grid, sep="\n"),
        "y": np.fromstring(density, sep="\n"),
    }


def _run_r(script: str, sample: np.ndarray, *extra: str):
    if shutil.which("Rscript") is None:
        return None
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        data = root / "x.txt"
        program = root / "check.R"
        np.savetxt(data, sample)
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(data), *extra],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout
