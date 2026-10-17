"""Checks for bkfe, including a comparison with R when it is installed."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from kernsmooth import bkfe
from mass import geyser


def test_bkfe_rejects_an_odd_derivative_order():
    with pytest.raises(ValueError, match="drv"):
        bkfe(np.array([0.0, 1.0, 2.0]), drv=1, bandwidth=0.5)


def test_bkfe_rejects_a_non_positive_bandwidth():
    with pytest.raises(ValueError, match="bandwidth"):
        bkfe(np.array([0.0, 1.0, 2.0]), drv=0, bandwidth=0.0)


def test_bkfe_matches_r_on_the_geyser_example():
    reference = _r_bkfe(np.asarray(geyser["duration"], dtype=np.float64), drv=4, bandwidth=0.3)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    estimate = bkfe(geyser["duration"], drv=4, bandwidth=0.3)
    assert estimate == pytest.approx(reference, abs=1e-8)


def test_bkfe_matches_r_for_even_orders_and_binned_counts():
    sample = np.random.default_rng(2).normal(size=60)
    for order in (0, 2, 4):
        reference = _r_bkfe(sample, drv=order, bandwidth=0.4)
        if reference is None:
            pytest.skip("Rscript or KernSmooth is unavailable")
        assert bkfe(sample, drv=order, bandwidth=0.4) == pytest.approx(reference, abs=1e-8)

    binned = _r_binned(sample)
    if binned is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    estimate = bkfe(
        binned["counts"],
        drv=2,
        bandwidth=0.4,
        range_x=(float(np.min(sample)), float(np.max(sample))),
        binned=True,
    )
    assert estimate == pytest.approx(binned["value"], abs=1e-8)


def _r_bkfe(sample: np.ndarray, drv: int, bandwidth: float):
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        drv <- as.integer(args[[2]])
        bandwidth <- as.numeric(args[[3]])
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        est <- KernSmooth::bkfe(x, drv=drv, bandwidth=bandwidth)
        cat(sprintf("%.17g\\n", est))
        """
    )
    text = _run_r(script, sample, str(drv), str(bandwidth))
    if text is None:
        return None
    return float(text.strip())


def _r_binned(sample: np.ndarray):
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        a <- min(x)
        b <- max(x)
        counts <- KernSmooth:::linbin(x, seq(a, b, length.out=401), TRUE)
        est <- KernSmooth::bkfe(counts, drv=2L, bandwidth=0.4, range.x=c(a, b), binned=TRUE)
        cat(sprintf("%.17g\\n", counts), sep="")
        cat("---\\n")
        cat(sprintf("%.17g\\n", est))
        """
    )
    text = _run_r(script, sample)
    if text is None:
        return None
    counts, value = text.split("---")
    return {"counts": np.fromstring(counts, sep="\n"), "value": float(value.strip())}


def _run_r(script: str, sample: np.ndarray, *extra: str):
    if shutil.which("Rscript") is None:
        return None
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        data = root / "x.txt"
        program = root / "check.R"
        np.savetxt(data, sample, fmt="%.17g")
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
