"""One check each for simplex and print_simplex against installed boot 1.3-32."""

from __future__ import annotations

import re
import shutil
import subprocess

import numpy as np
import pytest

from boot.simplex import print_simplex, simplex

TOLERANCE = 1e-8
_NUMBER = re.compile(r"(?<![A-Za-z])[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?")

_R = r"""
suppressPackageStartupMessages(library(boot))
stopifnot(packageVersion("boot") == "1.3.32")
enj <- c(200, 6000, 3000, -200)
fat <- c(800, 6000, 1000, 400)
vitx <- c(50, 3, 150, 100)
vity <- c(10, 10, 75, 100)
vitz <- c(150, 35, 75, 5)
res <- simplex(a = enj, A1 = fat, b1 = 13800, A2 = rbind(vitx, vity, vitz),
               b2 = c(600, 300, 550), maxi = TRUE)
emit <- function(name, value) cat(name, paste(sprintf("%a", value), collapse = " "), "\n")
cat("solved", res$solved, "\n")
emit("value", res$value)
emit("soln", res$soln)
emit("slack", res$slack)
emit("surplus", res$surplus)
emit("a", res$a)
emit("basic", res$basic)
cat("A\n")
for (i in seq_len(nrow(res$A))) cat(paste(sprintf("%a", res$A[i, ]), collapse = " "), "\n")
cat("AEND\n")
cat("PRINT_START\n")
writeLines(capture.output(print(res)))
cat("PRINT_END\n")
"""


def _reference():
    if shutil.which("Rscript") is None:
        pytest.fail("Rscript is not installed")
    result = subprocess.run(
        ["Rscript", "-e", _R],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(result.stderr)
    return result.stdout


def _hex_row(line):
    return np.array([float.fromhex(piece) for piece in line.split()], dtype=np.float64)


def _section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]


def _numbers(text):
    body = text.split("Objective Function Coefficients", 1)[1]
    return [float(match) for match in _NUMBER.findall(body)]


def test_simplex_matches_r():
    stdout = _reference()
    rows = {}
    matrix = []
    reading = False
    for line in stdout.splitlines():
        if line.startswith("PRINT_"):
            break
        if line == "A":
            reading = True
            continue
        if line == "AEND":
            reading = False
            continue
        if reading:
            matrix.append(_hex_row(line))
            continue
        name, rest = line.split(maxsplit=1)
        rows[name] = rest

    got = simplex(
        a=[200, 6000, 3000, -200],
        A1=[800, 6000, 1000, 400],
        b1=13800,
        A2=[[50, 3, 150, 100], [10, 10, 75, 100], [150, 35, 75, 5]],
        b2=[600, 300, 550],
        maxi=True,
    )
    assert got.solved == int(rows["solved"])
    assert got.basic.tolist() == [int(float.fromhex(piece)) for piece in rows["basic"].split()]
    arrays = {
        "value": np.array([got.value]),
        "soln": got.soln,
        "slack": got.slack,
        "surplus": got.surplus,
        "a": got.a,
        "A": got.A,
    }
    expected = {
        "value": _hex_row(rows["value"]),
        "soln": _hex_row(rows["soln"]),
        "slack": _hex_row(rows["slack"]),
        "surplus": _hex_row(rows["surplus"]),
        "a": _hex_row(rows["a"]),
        "A": np.vstack(matrix),
    }
    diff = max(float(np.max(np.abs(arrays[name] - expected[name]))) for name in arrays)
    assert diff <= TOLERANCE


def test_print_simplex_matches_r():
    stdout = _reference()
    printed = _section(stdout, "PRINT_START\n", "PRINT_END\n")
    got = simplex(
        a=[200, 6000, 3000, -200],
        A1=[800, 6000, 1000, 400],
        b1=13800,
        A2=[[50, 3, 150, 100], [10, 10, 75, 100], [150, 35, 75, 5]],
        b2=[600, 300, 550],
        maxi=True,
    )
    text = print_simplex(got)
    assert text.startswith("\nLinear Programming Results\n")
    left = _numbers(printed)
    right = _numbers(text)
    assert len(left) == len(right)
    diff = max(abs(a - b) for a, b in zip(left, right))
    assert diff <= TOLERANCE
