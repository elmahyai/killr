"""Checks for dpik, including a comparison with R when it is installed."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from kernsmooth import dpik
from mass import geyser


def test_dpik_rejects_a_level_above_five():
    with pytest.raises(ValueError, match="Level"):
        dpik(np.array([0.0, 1.0, 2.0]), level=6)


def test_dpik_matches_r_on_the_geyser_example():
    sample = np.asarray(geyser["duration"], dtype=np.float64)
    reference = _r_dpik(sample)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    assert dpik(sample) == pytest.approx(reference, abs=1e-8)


def test_dpik_matches_r_for_levels_kernels_and_scale():
    sample = np.random.default_rng(3).normal(size=80)
    cases = (
        {},
        {"level": 0},
        {"level": 1},
        {"level": 5},
        {"kernel": "epanech", "canonical": True},
        {"scalest": "iqr"},
    )
    for kwargs in cases:
        reference = _r_dpik(sample, **kwargs)
        if reference is None:
            pytest.skip("Rscript or KernSmooth is unavailable")
        assert dpik(sample, **kwargs) == pytest.approx(reference, abs=1e-8)


def _r_dpik(sample: np.ndarray, **kwargs):
    level = kwargs.get("level", 2)
    kernel = kwargs.get("kernel", "normal")
    canonical = "TRUE" if kwargs.get("canonical", False) else "FALSE"
    scalest = kwargs.get("scalest", "minim")
    script = textwrap.dedent(
        f"""
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        est <- KernSmooth::dpik(
          x, scalest="{scalest}", level={int(level)}L, kernel="{kernel}",
          canonical={canonical}
        )
        cat(sprintf("%.17g\\n", est))
        """
    )
    text = _run_r(script, sample)
    if text is None:
        return None
    return float(text.strip())


def _run_r(script: str, sample: np.ndarray):
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
            ["Rscript", str(program), str(data)],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout
