"""Checks for locpoly, including a comparison with R when it is installed."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import numpy as np
import pytest

from kernsmooth import locpoly
from mass import geyser


def test_locpoly_requires_a_positive_bandwidth():
    with pytest.raises(ValueError, match="bandwidth"):
        locpoly(np.array([0.0, 1.0, 2.0]), bandwidth=0.0)


def test_locpoly_density_matches_r_on_the_geyser_example():
    sample = np.asarray(geyser["duration"], dtype=np.float64)
    reference = _r_locpoly(sample, None, 0.25)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    estimate = locpoly(sample, bandwidth=0.25)
    assert estimate["x"] == pytest.approx(reference["x"], abs=1e-8)
    assert estimate["y"] == pytest.approx(reference["y"], abs=1e-8)


def test_locpoly_regression_matches_r_on_the_geyser_example():
    duration = np.asarray(geyser["duration"], dtype=np.float64)
    waiting = np.asarray(geyser["waiting"], dtype=np.float64)
    reference = _r_locpoly(duration, waiting, 0.25)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    estimate = locpoly(duration, waiting, bandwidth=0.25)
    assert estimate["y"] == pytest.approx(reference["y"], abs=1e-8)


def test_rlbin_matches_r():
    duration = np.asarray(geyser["duration"], dtype=np.float64)
    waiting = np.asarray(geyser["waiting"], dtype=np.float64)
    reference = _r_rlbin(duration, waiting)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    from rlbin import rlbin

    xcounts, ycounts = rlbin(duration, waiting, float(duration.min()), float(duration.max()), 41, True)
    assert np.asarray(xcounts) == pytest.approx(reference["x"], abs=1e-8)
    assert np.asarray(ycounts) == pytest.approx(reference["y"], abs=1e-8)


def _r_locpoly(x: np.ndarray, y: np.ndarray | None, bandwidth: float):
    call = (
        f"KernSmooth::locpoly(x, bandwidth={bandwidth})"
        if y is None
        else f"KernSmooth::locpoly(x, y, bandwidth={bandwidth})"
    )
    script = textwrap.dedent(
        f"""
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        {"y <- scan(args[[2]], quiet=TRUE)" if y is not None else ""}
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        est <- {call}
        cat(sprintf("%.17g\\n", est$x), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", est$y), sep="")
        """
    )
    text = _run_r(script, x, y)
    if text is None:
        return None
    grid, curve = text.split("---")
    return {"x": np.fromstring(grid, sep="\n"), "y": np.fromstring(curve, sep="\n")}


def _r_rlbin(x: np.ndarray, y: np.ndarray):
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        y <- scan(args[[2]], quiet=TRUE)
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        a <- min(x)
        b <- max(x)
        out <- KernSmooth:::rlbin(x, y, seq(a, b, length.out=41), TRUE)
        cat(sprintf("%.17g\\n", out$xcounts), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", out$ycounts), sep="")
        """
    )
    text = _run_r(script, x, y)
    if text is None:
        return None
    xcounts, ycounts = text.split("---")
    return {"x": np.fromstring(xcounts, sep="\n"), "y": np.fromstring(ycounts, sep="\n")}


def _run_r(script: str, x: np.ndarray, y: np.ndarray | None):
    if shutil.which("Rscript") is None:
        return None
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        data = root / "x.txt"
        program = root / "check.R"
        np.savetxt(data, x, fmt="%.17g")
        command = ["Rscript", str(program), str(data)]
        if y is not None:
            response = root / "y.txt"
            np.savetxt(response, y, fmt="%.17g")
            command.append(str(response))
        program.write_text(script)
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout
