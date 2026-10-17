"""Checks for dpill, including a comparison with R when it is installed."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import numpy as np
import pytest

from kernsmooth.dpill import dpill
from mass import geyser


def test_dpill_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        dpill(np.array([0.0, 1.0]), np.array([1.0]))


def test_dpill_matches_r_on_the_geyser_example():
    duration = np.asarray(geyser["duration"], dtype=np.float64)
    waiting = np.asarray(geyser["waiting"], dtype=np.float64)
    reference = _r_dpill(duration, waiting)
    if reference is None:
        pytest.skip("Rscript or KernSmooth is unavailable")
    selected = dpill(duration, waiting)
    assert selected == pytest.approx(reference, abs=1e-8)


def _r_dpill(x: np.ndarray, y: np.ndarray):
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        x <- scan(args[[1]], quiet=TRUE)
        y <- scan(args[[2]], quiet=TRUE)
        if (!requireNamespace("KernSmooth", quietly=TRUE)) quit(status=2)
        cat(sprintf("%.17g\\n", KernSmooth::dpill(x, y)))
        """
    )
    if shutil.which("Rscript") is None:
        return None
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        data_x = root / "x.txt"
        data_y = root / "y.txt"
        program = root / "check.R"
        np.savetxt(data_x, x, fmt="%.17g")
        np.savetxt(data_y, y, fmt="%.17g")
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(data_x), str(data_y)],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return float(result.stdout.strip())
