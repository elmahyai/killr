"""The Ilocos table matches the installed ineq data."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from ineq.ilocos import Ilocos


def test_ilocos_matches_the_installed_frame():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    script = """
suppressPackageStartupMessages(library(ineq))
data(Ilocos)
cat(nrow(Ilocos), "\n", sep="")
cat(sprintf("%.17g\n", Ilocos$income[1]))
cat(as.character(Ilocos$sex[1]), "\n", sep="")
cat(as.character(Ilocos$province[1]), "\n", sep="")
cat(sprintf("%.17g\n", Ilocos$AP.income[2]))
"""
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(completed.stderr.strip() or "ineq is unavailable")
    rows = completed.stdout.splitlines()
    assert len(Ilocos["income"]) == int(rows[0])
    assert Ilocos["income"][0] == pytest.approx(float(rows[1]), abs=1e-8)
    assert Ilocos["sex"][0] == rows[2]
    assert Ilocos["province"][0] == rows[3]
    assert Ilocos["AP.income"][1] == pytest.approx(float(rows[4]), abs=1e-8)
