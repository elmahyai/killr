"""Checks for dpih, including a comparison with R when it is installed."""

from __future__ import annotations

import shutil
import subprocess
import textwrap

import numpy as np
import pytest

from kernsmooth import dpih
from kernsmooth.dpih import histogram_breaks
from mass import geyser


def test_dpih_rejects_a_level_above_five():
    with pytest.raises(ValueError, match="Level"):
        dpih(np.array([0.0, 1.0, 2.0]), level=6)


def test_dpih_matches_r_on_the_geyser_example():
    sample = np.asarray(geyser["duration"], dtype=np.float64)
    reference = _r_dpih(sample)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    assert dpih(sample) == pytest.approx(reference, abs=1e-8)


def test_dpih_matches_r_for_levels_and_scale():
    sample = np.random.default_rng(4).normal(size=80)
    cases = ({}, {"level": 0}, {"level": 1}, {"level": 5}, {"scalest": "stdev"})
    for kwargs in cases:
        reference = _r_dpih(sample, **kwargs)
        if reference is None:
            pytest.skip("Rscript or KernSmooth is unavailable")
        assert dpih(sample, **kwargs) == pytest.approx(reference, abs=1e-8)


def test_histogram_breaks_match_r_seq():
    sample = np.asarray(geyser["duration"], dtype=np.float64)
    width = dpih(sample)
    reference = _r_seq(sample, width)
    if reference is None:
        pytest.skip("Rscript is unavailable")
    assert histogram_breaks(sample, width) == pytest.approx(reference, abs=1e-8)


def _r_dpih(sample: np.ndarray, **kwargs):
    level = kwargs.get("level", 2)
    scalest = kwargs.get("scalest", "minim")
    script = textwrap.dedent(
        f"""
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        est <- KernSmooth::dpih(x, scalest="{scalest}", level={int(level)}L)
        cat(sprintf("%.17g\\n", est))
        """
    )
    text = _run_r(script, sample)
    if text is None:
        return None
    return float(text.strip())


def _r_seq(sample: np.ndarray, width: float):
    script = textwrap.dedent(
        f"""
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        h <- {width:.17g}
        cat(sprintf("%.17g\\n", seq(min(x) - h, max(x) + h, by=h)), sep="")
        """
    )
    text = _run_r(script, sample)
    if text is None:
        return None
    return np.fromstring(text, sep="\n")


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
