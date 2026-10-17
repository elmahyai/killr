"""Dimensions and the first row of each boot dataset match the installed package."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from boot import data_sets

NAMES = [
    "acme",
    "aids",
    "aircondit",
    "aircondit7",
    "amis",
    "aml",
    "beaver",
    "bigcity",
    "brambles",
    "breslow",
    "calcium",
    "cane",
    "capability",
    "catsM",
    "cav",
    "cd4",
    "cd4.nested",
    "channing",
    "city",
    "claridge",
    "cloth",
    "co.transfer",
    "coal",
    "darwin",
    "dogs",
    "downs.bc",
    "ducks",
    "fir",
    "frets",
    "grav",
    "gravity",
    "hirose",
    "islay",
    "manaus",
    "melanoma",
    "motor",
    "neuro",
    "nitrofen",
    "nodal",
    "nuclear",
    "paulsen",
    "poisons",
    "polar",
    "remission",
    "salinity",
    "survival",
    "tau",
    "tuna",
    "urine",
    "wool",
]

DOCS = Path(__file__).resolve().parents[1] / "docs"

_R = r"""
suppressPackageStartupMessages(library(boot))
names <- c(__NAMES__)
emit <- function(v) {
  if (is.factor(v)) v <- as.character(v)
  if (is.character(v)) {
    if (is.na(v)) cat("NA\n") else cat("S\t", v, "\n", sep = "")
    return()
  }
  if (length(v) != 1) stop("expected one cell")
  if (is.na(v)) {
    cat("NA\n")
    return()
  }
  if (is.integer(v)) {
    cat("I\t", v, "\n", sep = "")
    return()
  }
  cat("D\t", sprintf("%.17g", as.numeric(v)), "\n", sep = "")
}
for (nm in names) {
  x <- get(nm)
  cat("@@ ", nm, "\n", sep = "")
  if (nm == "cd4.nested") {
    cat("DIM ", nrow(x$t), " ", ncol(x$t), "\n", sep = "")
    for (v in x$t[1, ]) emit(v)
    next
  }
  if (is.data.frame(x) || is.matrix(x) || length(dim(x)) == 2) {
    cat("DIM ", nrow(x), " ", ncol(x), "\n", sep = "")
    if (is.data.frame(x)) {
      for (j in seq_len(ncol(x))) emit(x[[j]][1])
    } else {
      for (v in x[1, ]) emit(v)
    }
  } else {
    cat("LEN ", length(x), "\n", sep = "")
    emit(x[1])
  }
}
"""


def _script() -> str:
    quoted = ", ".join(f'"{name}"' for name in NAMES)
    return _R.replace("__NAMES__", quoted)


def _parse(text: str) -> dict[str, tuple[list[int], list]]:
    found: dict[str, tuple[list[int], list]] = {}
    name = ""
    dims: list[int] = []
    cells: list = []
    for line in text.splitlines():
        if line.startswith("@@ "):
            if name:
                found[name] = (dims, cells)
            name = line[3:]
            dims = []
            cells = []
        elif line.startswith("DIM "):
            dims = [int(part) for part in line[4:].split()]
        elif line.startswith("LEN "):
            dims = [int(line[4:])]
        elif line == "NA":
            cells.append(None)
        elif line.startswith("S\t"):
            cells.append(line[2:])
        elif line.startswith("I\t"):
            cells.append(int(line[2:]))
        elif line.startswith("D\t"):
            cells.append(float(line[2:]))
        else:
            raise AssertionError(line)
    if name:
        found[name] = (dims, cells)
    return found


def _cell(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    number = float(value)
    if math.isnan(number):
        return None
    return number


def _python(name: str) -> tuple[list[int], list]:
    value = getattr(data_sets, name.replace(".", "_"))()
    if name == "cd4.nested":
        table = value["t"]
        return [int(table.shape[0]), int(table.shape[1])], [_cell(item) for item in table[0]]
    if hasattr(value, "shape") and not isinstance(value, tuple):
        if len(value.shape) == 1:
            return [int(value.shape[0])], [_cell(value[0])]
        return [int(value.shape[0]), int(value.shape[1])], [_cell(item) for item in value[0]]
    columns, rows = value
    if hasattr(rows, "shape"):
        return [int(rows.shape[0]), int(rows.shape[1])], [_cell(item) for item in rows[0]]
    return [len(rows), len(columns)], [_cell(item) for item in rows[0]]


@pytest.fixture(scope="module")
def installed():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    completed = subprocess.run(
        ["Rscript", "-e", _script()],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.fail(completed.stderr.strip() or "boot is unavailable")
    parsed = _parse(completed.stdout)
    missing = [name for name in NAMES if name not in parsed]
    if missing:
        pytest.fail(f"R did not report {missing}")
    return parsed


@pytest.mark.parametrize("name", NAMES)
def test_dimensions_and_first_row(name, installed):
    dims, row = _python(name)
    expected_dims, expected_row = installed[name]
    assert dims == expected_dims
    assert row == expected_row


@pytest.mark.parametrize("name", NAMES)
def test_example_output_is_captured(name):
    document = json.loads((DOCS / f"{name}.json").read_text())
    assert document["name"] == name
    for side, suffix in (("origin", "r"), ("translation", "python")):
        block = document[side]
        for key in (
            "description",
            "usage",
            "arguments",
            "details",
            "value",
            "example",
            "output",
        ):
            assert key in block
        assert block["output"] == f"output/{name}-{suffix}.txt"
        text = (DOCS / block["output"]).read_text()
        assert text.strip()
