"""Checks for rowAvgsPerColSet and colAvgsPerRowSet against matrixStats 1.5.0."""

from __future__ import annotations

import shutil
import subprocess
import textwrap
import warnings

import numpy as np
import pytest

from matrixstats.rowavgs import colAvgsPerRowSet, rowAvgsPerColSet
from matrixstats.rowmeans2 import rowMeans2
from matrixstats.rowsums2 import colSums2

TOL = 1e-8

CASES = [
    ("negdup", [-4, 0, 0, -3, -1, -3, -1], "c(-4, 0, 0, -3, -1, -3, -1)"),
    ("pos", [3, 5, 1], "c(3, 5, 1)"),
    ("dup", [3, 0, 0, 5, 1, 5, 5], "c(3, 0, 0, 5, 1, 5, 5)"),
    ("oob", list(range(4, 10)), "4:9"),
    ("negoob", [-5, 0, -3, -1, -9], "c(-5, 0, -3, -1, -9)"),
    ("dropall", [-1, -2, -3, -4, -5, -6], "-1:-6"),
    ("four", 4, "4"),
    ("mfour", -4, "-4"),
    ("zero", 0, "0"),
    ("empty", [], "integer(0)"),
    ("na", [np.nan, 0, 2], "c(NA_real_, 0, 2)"),
    ("neginf", [-np.inf, -1], "c(-Inf, -1)"),
    ("inf", [np.nan, 0, 2, np.inf], "c(NA_real_, 0, 2, Inf)"),
    ("true", True, "TRUE"),
    ("false", False, "FALSE"),
    ("lna", [None], "NA"),
    (
        "lfull",
        [False, True, False, True, True, False],
        "c(FALSE, TRUE, FALSE, TRUE, TRUE, FALSE)",
    ),
    (
        "llong",
        [False, True, False, True, True, True, False, True],
        "c(FALSE, TRUE, FALSE, TRUE, TRUE, TRUE, FALSE, TRUE)",
    ),
    ("lshort", [False, True], "c(FALSE, TRUE)"),
    ("lna3", [False, True, None], "c(FALSE, TRUE, NA)"),
    ("lna4", [False, True, None, False], "c(FALSE, TRUE, NA, FALSE)"),
    ("mix", [1, -1], "c(1, -1)"),
    ("mix0", [-4, 0, 0, 1], "c(-4, 0, 0, 1)"),
    ("nneg", [np.nan, -2], "c(NA_real_, -2)"),
    ("frac", [1.9, 2.2, 0.5], "c(1.9, 2.2, 0.5)"),
]


def test_readable_sets_match_the_printed_matrix():
    x = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    sets = np.array([[1, 2], [2, 3]])
    rows = rowAvgsPerColSet(x, S=sets)
    assert rows.dtype == np.float64
    assert rows.tolist() == [[2.0, 4.0], [3.0, 5.0]]
    columns = colAvgsPerRowSet(x, S=np.array([[1], [2]]))
    assert columns.tolist() == [[1.5, 3.5, 5.5]]


def test_nonfinite_indexes_are_dropped_and_na_rm_follows_any_missing():
    x = np.array([[1.0, 4.0, 7.0, 10.0], [2.0, 5.0, 8.0, 11.0], [3.0, 6.0, 9.0, 12.0]])
    sets = np.array([[1.0, 2.0, 3.0, 4.0], [np.inf, np.nan, np.nan, -np.inf]])
    assert rowAvgsPerColSet(x, S=sets).tolist() == [
        [1.0, 4.0, 7.0, 10.0],
        [2.0, 5.0, 8.0, 11.0],
        [3.0, 6.0, 9.0, 12.0],
    ]
    with_na = x.copy()
    with_na[0, 0] = np.nan
    dropped = rowAvgsPerColSet(with_na, S=np.array([[1, 3], [2, 4]]))
    assert dropped[0, 0] == 4.0
    kept = rowAvgsPerColSet(with_na, S=np.array([[1, 3], [2, 4]]), na_rm=False)
    assert np.isnan(kept[0, 0])
    assert kept[0, 1] == 8.5
    only_missing = np.array([[np.nan], [np.inf]])
    assert np.isnan(rowAvgsPerColSet(x, S=only_missing)).all()


def test_rows_follow_base_subscript_rules():
    x = np.arange(1.0, 13.0).reshape((3, 4), order="F")
    one = np.array([[1, 2]]).T
    assert rowAvgsPerColSet(x, rows=[3, 1], S=one).ravel().tolist() == [4.5, 2.5]
    assert rowAvgsPerColSet(x, rows=[0, 2], S=one).ravel().tolist() == [3.5]
    assert rowAvgsPerColSet(x, rows=[-1], S=one).ravel().tolist() == [3.5, 4.5]
    assert rowAvgsPerColSet(x, rows=[True, False, True], S=one).ravel().tolist() == [
        2.5,
        4.5,
    ]
    assert rowAvgsPerColSet(x, rows=0, S=np.array([[1]])).shape == (0, 1)
    with pytest.raises(ValueError, match="subscript out of bounds"):
        rowAvgsPerColSet(x, rows=list(range(4, 10)), S=np.array([[1]]))
    with pytest.raises(ValueError, match="only 0's may be mixed with negative subscripts"):
        rowAvgsPerColSet(x, rows=[1, -1], S=np.array([[1]]))


def test_one_row_stays_a_matrix_and_empty_margins_keep_their_shape():
    one_row = np.array([[1.0, 2.0, 3.0]])
    assert rowAvgsPerColSet(one_row, S=np.array([[1]])).shape == (1, 1)
    assert rowAvgsPerColSet(one_row, rows=0, S=np.array([[1]])).shape == (0, 1)
    wide = np.zeros((0, 8))
    sets = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
    assert rowAvgsPerColSet(wide, S=sets, FUN=rowMeans2).shape == (0, 4)
    tall = np.zeros((6, 0))
    row_sets = np.array([[1, 3, 5], [2, 4, 6]])
    assert colAvgsPerRowSet(tall, S=row_sets, FUN=colSums2).shape == (3, 0)
    with pytest.raises(ValueError, match=r"dimX\[1\] > 1L"):
        rowAvgsPerColSet(np.arange(12.0).reshape(3, 4), S=np.zeros((2, 0)))


def test_t_fun_transposes_before_fun_and_column_sets_flip_it():
    x = np.arange(1.0, 13.0).reshape((3, 4), order="F")
    one = np.array([[1], [2]])
    with pytest.raises(ValueError, match="length\\(Zjj\\) != dimX\\[1L\\]"):
        rowAvgsPerColSet(x, S=one, t_fun=True)
    assert rowAvgsPerColSet(x, S=one, FUN=_col_means_alias, t_fun=True).ravel().tolist() == [
        2.5,
        3.5,
        4.5,
    ]
    assert colAvgsPerRowSet(x, S=np.array([[1, 3], [2, 3]])).tolist() == [
        [1.5, 4.5, 7.5, 10.5],
        [3.0, 6.0, 9.0, 12.0],
    ]
    with pytest.raises(ValueError, match="length\\(Zjj\\) != dimX\\[1L\\]"):
        colAvgsPerRowSet(x, S=one, t_fun=True)


def test_weights_reach_fun_as_a_zero_column_matrix():
    x = np.arange(1.0, 13.0).reshape((3, 4), order="F")
    weights = np.ones_like(x)
    seen = {}

    def record(subset, W, na_rm=False):
        seen["shape"] = W.shape
        return subset.mean(axis=1)

    out = rowAvgsPerColSet(x, W=weights, S=np.array([[1], [2]]), FUN=record)
    assert seen["shape"] == (3, 0)
    assert out.ravel().tolist() == [2.5, 3.5, 4.5]
    with pytest.raises(ValueError, match="unused argument \\(W = Wjj\\)"):
        rowAvgsPerColSet(x, W=weights, S=np.array([[1]]))
    with pytest.raises(ValueError, match="different dimensions: 2x2 != 3x4"):
        rowAvgsPerColSet(x, W=np.ones((2, 2)), S=np.array([[1]]))
    with pytest.raises(ValueError, match="different dimensions: 4x3 != 2x3"):
        colAvgsPerRowSet(x, W=weights, cols=[1, 2], S=np.array([[1], [2], [3]]))


def test_argument_checks_use_the_installed_messages():
    x = np.arange(12.0).reshape(3, 4)
    sets = np.array([[1], [2]])
    with pytest.raises(ValueError, match="Argument 'X' is not a matrix: integer"):
        rowAvgsPerColSet(np.arange(4), S=sets)
    with pytest.raises(ValueError, match="Argument 'S' is not a matrix: integer"):
        rowAvgsPerColSet(x, S=np.arange(2))
    with pytest.raises(ValueError, match="Argument 'FUN' is not a function: numeric"):
        rowAvgsPerColSet(x, S=sets, FUN=1)
    with pytest.raises(ValueError, match="Argument 'W' is not numeric: logical"):
        rowAvgsPerColSet(x, W=np.ones((3, 4), dtype=bool), S=sets, FUN=lambda z, W, na_rm: z[:, 0])
    with pytest.raises(ValueError, match="missing value where TRUE/FALSE needed"):
        rowAvgsPerColSet(x, S=np.array([[1]]), t_fun=np.nan)
    with pytest.raises(ValueError, match="the condition has length > 1"):
        rowAvgsPerColSet(x, S=np.array([[1]]), na_rm=[True, False])
    with pytest.raises(ValueError, match='argument "S" is missing, with no default'):
        colAvgsPerRowSet(x)


def test_matches_r_on_indexes_missing_values_and_weights():
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript is unavailable")
    reference = _r_suite()
    if reference is None:
        pytest.skip("matrixStats is unavailable")
    x = np.arange(1.0, 37.0).reshape((6, 6), order="F")
    for row_id, (row_name, row_index, _) in enumerate(CASES):
        for col_id, (col_name, col_index, _) in enumerate(CASES):
            _expect(
                f"row {row_name} {col_name}",
                reference[f"row-{row_id}-{col_id}"],
                lambda rows=row_index, cols=col_index: rowAvgsPerColSet(
                    x, rows=rows, S=_as_column(cols)
                ),
            )
            _expect(
                f"col {row_name} {col_name}",
                reference[f"col-{row_id}-{col_id}"],
                lambda rows=row_index, cols=col_index: colAvgsPerRowSet(
                    x, cols=cols, S=_as_column(rows)
                ),
            )
    _assert_close(rowAvgsPerColSet(reference["big"], S=_proof_sets()), reference["big_row"])
    _assert_close(colAvgsPerRowSet(reference["big"], S=_proof_sets()), reference["big_col"])
    dirty = np.array(reference["big"], copy=True)
    dirty[0, 0] = np.nan
    broken = _proof_sets().astype(float)
    broken[0, 0] = np.nan
    _assert_close(rowAvgsPerColSet(dirty, S=broken), reference["na_row"])
    _assert_close(
        colAvgsPerRowSet(dirty, S=np.column_stack([np.arange(1, 6), np.arange(6, 11)])),
        reference["na_col"],
    )
    small = np.arange(1.0, 13.0).reshape((3, 4), order="F")

    def widths(subset, W, na_rm=False):
        return np.repeat(W.shape[1], subset.shape[0])

    _assert_close(
        rowAvgsPerColSet(small, W=np.ones_like(small), S=np.array([[1], [2]]), FUN=widths),
        reference["weights"],
    )


def _col_means_alias(x, na_rm=False):
    from matrixstats.rowavgs import _col_means

    return _col_means(x, na_rm=na_rm)


def _proof_sets():
    return np.column_stack([np.arange(1, 6), np.arange(6, 11), np.arange(11, 16)])


def _as_column(index):
    if isinstance(index, list):
        if len(index) == 0:
            return np.zeros((0, 1), dtype=np.int64)
        if any(item is None for item in index):
            column = np.empty((len(index), 1), dtype=object)
            column[:, 0] = index
            return column
        return np.asarray(index).reshape(-1, 1)
    if isinstance(index, (bool, np.bool_)):
        return np.array([[bool(index)]])
    return np.array([[index]])


def _expect(label, reference, call):
    if reference is None:
        with pytest.raises(ValueError):
            call()
        return
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            got = call()
    except ValueError as exc:
        raise AssertionError(f"{label} raised {exc}") from exc
    _assert_close(got, reference, label)


def _assert_close(actual, expected, label=""):
    actual = np.asarray(actual, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    assert actual.shape == expected.shape, label
    both_nan = np.isnan(actual) & np.isnan(expected)
    diff = np.abs(actual - expected)
    ok = both_nan | (diff <= TOL)
    assert bool(np.all(ok)), (label, np.nanmax(np.where(ok, 0.0, diff)))


def _r_suite():
    case_lines = []
    for index, (_, _, code) in enumerate(CASES):
        case_lines.append(f"rows_{index} <- {code}")
        case_lines.append(f"cols_{index} <- {code}")
    calls = []
    for row_id in range(len(CASES)):
        for col_id in range(len(CASES)):
            calls.append(
                "emit(\"row-{row}-{col}\", "
                "rowAvgsPerColSet(x, rows = rows_{row}, S = matrix(cols_{col}, ncol = 1), "
                "FUN = rowMeans))".format(row=row_id, col=col_id)
            )
            calls.append(
                "emit(\"col-{row}-{col}\", "
                "colAvgsPerRowSet(x, cols = cols_{col}, S = matrix(rows_{row}, ncol = 1), "
                "FUN = colMeans))".format(row=row_id, col=col_id)
            )
    script = textwrap.dedent(
        """\
        args <- commandArgs(trailingOnly=TRUE)
        bin <- args[[1]]
        if (!requireNamespace("matrixStats", quietly=TRUE)) quit(status=2)
        library(matrixStats)
        emit <- function(name, expr) {{
          cat(name, "\\n", sep="")
          out <- suppressWarnings(tryCatch(expr, error = function(e) e))
          if (inherits(out, "error")) {{
            cat("error\\n---\\n")
          }} else {{
            cat(nrow(out), " ", ncol(out), "\\n", sep="")
            if (length(out)) cat(sprintf("%.17g\\n", as.numeric(out)), sep="")
            cat("---\\n")
          }}
        }}
        x <- matrix(1:36, nrow = 6)
        {cases}
        {calls}
        set.seed(1)
        big <- matrix(rnorm(80 * 40), nrow = 80, ncol = 40)
        writeBin(as.numeric(big), bin)
        Sb <- cbind(1:5, 6:10, 11:15)
        emit("big_row", rowAvgsPerColSet(big, S = Sb))
        emit("big_col", colAvgsPerRowSet(big, S = Sb))
        big[1, 1] <- NA
        Sb[1, 1] <- NA
        emit("na_row", rowAvgsPerColSet(big, S = Sb))
        emit("na_col", colAvgsPerRowSet(big, S = cbind(1:5, 6:10)))
        small <- matrix(1:12, nrow = 3)
        W <- matrix(1, nrow = 3, ncol = 4)
        emit("weights", rowAvgsPerColSet(small, W = W, S = matrix(c(1, 2), ncol = 1),
             FUN = function(x, W = NULL, na.rm = FALSE) rep(ncol(W), nrow(x))))
        """
    ).format(cases="\n".join(case_lines), calls="\n".join(calls))
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        program = root / "check.R"
        data = root / "big.bin"
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
        parsed = _parse_blocks(result.stdout)
        matrix = np.fromfile(data, dtype="<f8").reshape((80, 40), order="F")
        parsed["big"] = np.array(matrix, order="C")
    return parsed


def _parse_blocks(text: str) -> dict:
    parsed = {}
    name = None
    chunk: list[str] = []
    for line in text.splitlines():
        if line == "---":
            parsed[name] = _decode(chunk)
            name = None
            chunk = []
        elif name is None:
            name = line
        else:
            chunk.append(line)
    return parsed


def _decode(lines: list[str]):
    if not lines or lines[0] == "error":
        return None
    nrow, ncol = (int(part) for part in lines[0].split())
    values = [_number(line) for line in lines[1:]]
    return np.asarray(values, dtype=np.float64).reshape((nrow, ncol), order="F")


def _number(line: str) -> float:
    if line in ("NA", "NaN"):
        return np.nan
    if line == "Inf":
        return np.inf
    if line == "-Inf":
        return -np.inf
    return float(line)
