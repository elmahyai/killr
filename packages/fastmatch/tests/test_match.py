"""Compare fastmatch against the installed R package."""

from __future__ import annotations

import json
import math
import subprocess
import warnings
from pathlib import Path

from fastmatch import Factor, List, PosixLt, coalesce, ctapply, fin, fmatch, fmatch_hash, not_fin
from fastmatch.match import Characters, Integers

R = r"""
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmatch))
if (as.character(packageVersion("fastmatch")) != "1.1.8") stop("expected fastmatch 1.1-8")
cap <- function(expr) {
  warns <- character()
  val <- withCallingHandlers(expr, warning = function(w) {
    warns <<- c(warns, conditionMessage(w))
    invokeRestart("muffleWarning")
  })
  list(
    null = is.null(val),
    values = if (is.null(val)) logical() else unname(val),
    names = if (is.null(val) || is.null(names(val))) character() else names(val),
    warnings = warns
  )
}
out <- list()
out$int <- cap(fmatch(c(2L, 4L, NA), c(1L, 2L, NA, 2L)))
out$nomatch <- cap(fmatch(4L, 1:3, nomatch = 0))
out$real <- cap(fmatch(c(1, NA, NaN, -0, 0, 2.5), c(0, NA, NaN, 2.5)))
out$chr <- cap(fmatch(c("b", "a", NA, "z"), c("a", NA, "b")))
out$empty_x <- cap(fmatch(integer(0), 1:3))
out$empty_y <- cap(fmatch(1:3, integer(0)))
out$null_y <- cap(fmatch(1:2, NULL))
out$fin <- cap(c(1L, 5L, NA) %fin% c(1L, NA))
out$notfin <- cap(c(1L, 5L, NA) %!fin% c(1L, NA))
out$fin_miss <- cap(c(NA, 1) %fin% 1:3)
out$factor_x <- cap(fmatch(factor(c("1", "foo", NA)), c(1L, 2L, 3L)))
out$factor_y <- cap(fmatch(c("1", "2", "a"), factor(c("b", "a", "a"))))
out$two_factors <- cap(fmatch(factor(c("b", "a")), factor(c("a", "b", "b"))))
out$logical <- cap(fmatch(c(TRUE, NA), c(NA, FALSE, TRUE)))
out$logical_int <- cap(fmatch(c(TRUE, FALSE, NA), 0:2))
out$int_logical <- cap(fmatch(c(0L, 1L, NA), c(FALSE, TRUE, NA)))
out$incomp <- cap(fmatch(1:3, 1:3, incomparables = 2))
out$incomp_false <- cap(fmatch(c(1L, 2L), c(2L, 1L), incomparables = FALSE))
out$incomp_true <- cap(fmatch(1L, 1:2, incomparables = TRUE))
out$nomatch_real <- cap(fmatch(9L, 1:3, nomatch = 1.9))
out$nomatch_na <- cap(fmatch(5, 1:3, nomatch = NA_real_))
out$nomatch_chr <- cap(fmatch(5, 1:3, nomatch = "0"))
out$int_real <- cap(fmatch(c(1L, NA), c(1, 2)))
out$chr_num <- cap(fmatch(c("1", "1.5", "1000000"), c(1, 1.5, 1e6)))
out$posix <- cap(fmatch(as.POSIXlt("2020-01-01", tz = "UTC"), "2020-01-01"))
out$complex <- cap(fmatch(1i, 1i))
out$hash <- cap(fmatch.hash(c("a", "b"), c(1L, 2L, 1L)))
out$hash_same <- cap(fmatch.hash(2L, c(1L, 2L, 3L)))
out$hash_empty_x <- cap(fmatch.hash(integer(0), 1:5))
out$hash_empty_y <- cap(fmatch.hash(1:2, integer(0)))
out$hash_logical <- cap(fmatch.hash(TRUE, c(FALSE, TRUE)))
out$coal_chr <- cap(coalesce(c("b", "a", "b", "a", "c")))
out$coal_int <- cap(coalesce(c(3L, 1L, 3L, NA, 1L, NA)))
out$coal_chr_na <- cap(coalesce(c("a", NA, "a", NA)))
out$coal_real <- cap(coalesce(c(1.5, 0, -0, 1.5, 2)))
out$coal_zero <- cap(coalesce(c(0, -0, 0)))
x <- c(10, 11, 20, 21, 22)
i <- c(1L, 1L, 2L, 2L, 2L)
out$ct_sum <- cap(ctapply(x, i, sum))
out$ct_len <- cap(ctapply(x, i, length))
out$ct_real <- cap(ctapply(c(1, 2, 3), c(1.5, 1.5, 2), sum))
out$ct_chr <- cap(ctapply(1:3, c("a", "a", "b"), sum))
out$ct_empty <- cap(ctapply(numeric(0), numeric(0), sum))
out$ct_safe <- cap(ctapply(x, i, sum, .SAFE = FALSE))
out$ct_split <- cap(ctapply(c(1, 2, 3), c(1L, 2L, 1L), sum))
out$ct_na_int <- cap(ctapply(c(1, 2), c(NA_integer_, NA_integer_), sum))
out$ct_na_real <- cap(ctapply(c(1, 2), c(NA_real_, NA_real_), sum))
out$ct_na_chr <- cap(ctapply(c(1, 2), c(NA_character_, NA_character_), sum))
out$ct_factor <- cap(ctapply(c(1, 2, 3), factor(c("a", "a", "b")), sum))
out$ct_list <- cap(ctapply(list(1, 2, 3, 4), c(1L, 1L, 2L, 2L), function(z) length(z)))
out$ct_dots <- cap(ctapply(1:4, c(1L, 1L, 2L, 2L), function(z, k) sum(z) + k, 10))
out$ct_id <- cap(ctapply(1:4, c(1L, 1L, 2L, 2L), identity))
out$ct_named <- cap(ctapply(c(1, 2, 3), c("a", "a", "b"), identity))
cat(jsonlite::toJSON(out, auto_unbox = FALSE, digits = 17, na = "null"))
"""


def r_value():
    script = Path("/tmp/fastmatch_cases.R")
    script.write_text(R, encoding="utf-8")
    proc = subprocess.run(["Rscript", str(script)], check=True, capture_output=True, text=True)
    return json.loads(proc.stdout.strip().splitlines()[-1])


def missing(value):
    if value is None or value == "NA":
        return True
    return isinstance(value, float) and math.isnan(value)


def close(got, expected, tol=1e-8):
    if isinstance(got, list) or isinstance(expected, list):
        if not isinstance(got, list):
            got = [got]
        if not isinstance(expected, list):
            expected = [expected]
        assert len(got) == len(expected), (got, expected)
        for left, right in zip(got, expected):
            close(left, right, tol)
        return
    if missing(got) or missing(expected):
        assert missing(got) and missing(expected), (got, expected)
        return
    if isinstance(got, str) or isinstance(expected, str):
        assert got == expected, (got, expected)
        return
    if isinstance(got, bool) or isinstance(expected, bool):
        assert bool(got) is bool(expected), (got, expected)
        return
    assert abs(float(got) - float(expected)) <= tol, (got, expected)


def warnings_of(thunk):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = thunk()
    return value, [str(item.message) for item in caught]


def check(name, thunk, expected, named=False):
    value, found = warnings_of(thunk)
    if expected["null"][0]:
        assert value is None, (name, value)
    elif named:
        close(value.values, expected["values"])
        assert list(value.names) == list(expected["names"] or []), (name, value.names, expected["names"])
    else:
        close(value, expected["values"])
    assert found == list(expected["warnings"]), (name, found, expected["warnings"])
    print(name, "ok")


def main():
    expected = r_value()
    check("int", lambda: fmatch([2, 4, None], [1, 2, None, 2]), expected["int"])
    check("nomatch", lambda: fmatch(4, [1, 2, 3], nomatch=0), expected["nomatch"])
    check(
        "real",
        lambda: fmatch([1.0, None, float("nan"), -0.0, 0.0, 2.5], [0.0, None, float("nan"), 2.5]),
        expected["real"],
    )
    check("chr", lambda: fmatch(["b", "a", None, "z"], ["a", None, "b"]), expected["chr"])
    check("empty_x", lambda: fmatch([], [1, 2, 3]), expected["empty_x"])
    check("empty_y", lambda: fmatch([1, 2, 3], []), expected["empty_y"])
    check("null_y", lambda: fmatch([1, 2], None), expected["null_y"])
    check("fin", lambda: fin([1, 5, None], [1, None]), expected["fin"])
    check("notfin", lambda: not_fin([1, 5, None], [1, None]), expected["notfin"])
    check("fin_miss", lambda: fin([None, 1], [1, 2, 3]), expected["fin_miss"])
    check(
        "factor_x",
        lambda: fmatch(Factor(["1", "foo", None]), [1, 2, 3]),
        expected["factor_x"],
    )
    check(
        "factor_y",
        lambda: fmatch(["1", "2", "a"], Factor(["b", "a", "a"])),
        expected["factor_y"],
    )
    check(
        "two_factors",
        lambda: fmatch(Factor(["b", "a"]), Factor(["a", "b", "b"])),
        expected["two_factors"],
    )
    check("logical", lambda: fmatch([True, None], [None, False, True]), expected["logical"])
    check("logical_int", lambda: fmatch([True, False, None], [0, 1, 2]), expected["logical_int"])
    check("int_logical", lambda: fmatch([0, 1, None], [False, True, None]), expected["int_logical"])
    check("incomp", lambda: fmatch([1, 2, 3], [1, 2, 3], incomparables=2), expected["incomp"])
    check(
        "incomp_false",
        lambda: fmatch([1, 2], [2, 1], incomparables=False),
        expected["incomp_false"],
    )
    check("incomp_true", lambda: fmatch(1, [1, 2], incomparables=True), expected["incomp_true"])
    check("nomatch_real", lambda: fmatch(9, [1, 2, 3], nomatch=1.9), expected["nomatch_real"])
    check("nomatch_na", lambda: fmatch(5, [1, 2, 3], nomatch=float("nan")), expected["nomatch_na"])
    check("nomatch_chr", lambda: fmatch(5, [1, 2, 3], nomatch="0"), expected["nomatch_chr"])
    check("int_real", lambda: fmatch([1, None], [1.0, 2.0]), expected["int_real"])
    check(
        "chr_num",
        lambda: fmatch(["1", "1.5", "1000000"], [1.0, 1.5, 1e6]),
        expected["chr_num"],
    )
    check("posix", lambda: fmatch(PosixLt("2020-01-01"), "2020-01-01"), expected["posix"])
    check("complex", lambda: fmatch(1j, 1j), expected["complex"])
    check("hash", lambda: list(fmatch_hash(["a", "b"], [1, 2, 1])), expected["hash"])
    assert str(fmatch_hash(["a"], [1, 2, 1]).match_hash) == "<hash table>"
    check("hash_same", lambda: list(fmatch_hash(2, [1, 2, 3])), expected["hash_same"])
    check("hash_empty_x", lambda: fmatch_hash([], [1, 2, 3, 4, 5]), expected["hash_empty_x"])
    check("hash_empty_y", lambda: fmatch_hash([1, 2], []), expected["hash_empty_y"])
    check("hash_logical", lambda: fmatch_hash(True, [False, True]), expected["hash_logical"])
    check("coal_chr", lambda: coalesce(["b", "a", "b", "a", "c"]), expected["coal_chr"])
    check("coal_int", lambda: coalesce([3, 1, 3, None, 1, None]), expected["coal_int"])
    check("coal_chr_na", lambda: coalesce(["a", None, "a", None]), expected["coal_chr_na"])
    check("coal_real", lambda: coalesce([1.5, 0.0, -0.0, 1.5, 2.0]), expected["coal_real"])
    check("coal_zero", lambda: coalesce([0.0, -0.0, 0.0]), expected["coal_zero"])
    x = [10, 11, 20, 21, 22]
    index = [1, 1, 2, 2, 2]
    check("ct_sum", lambda: ctapply(x, index, sum), expected["ct_sum"], named=True)
    check("ct_len", lambda: ctapply(x, index, len), expected["ct_len"], named=True)
    check("ct_real", lambda: ctapply([1, 2, 3], [1.5, 1.5, 2.0], sum), expected["ct_real"], named=True)
    check("ct_chr", lambda: ctapply([1, 2, 3], ["a", "a", "b"], sum), expected["ct_chr"], named=True)
    check("ct_empty", lambda: ctapply([], [], sum), expected["ct_empty"])
    check("ct_safe", lambda: ctapply(x, index, sum, safe=False), expected["ct_safe"], named=True)
    check("ct_split", lambda: ctapply([1, 2, 3], [1, 2, 1], sum), expected["ct_split"], named=True)
    check(
        "ct_na_int",
        lambda: ctapply([1, 2], Integers([None, None]), sum),
        expected["ct_na_int"],
        named=True,
    )
    check(
        "ct_na_real",
        lambda: ctapply([1, 2], [float("nan"), float("nan")], sum),
        expected["ct_na_real"],
        named=True,
    )
    check(
        "ct_na_chr",
        lambda: ctapply([1, 2], Characters([None, None]), sum),
        expected["ct_na_chr"],
        named=True,
    )
    check(
        "ct_factor",
        lambda: ctapply([1, 2, 3], Factor(["a", "a", "b"]), sum),
        expected["ct_factor"],
        named=True,
    )
    check(
        "ct_list",
        lambda: ctapply(List([1, 2, 3, 4]), [1, 1, 2, 2], len),
        expected["ct_list"],
        named=True,
    )
    check(
        "ct_dots",
        lambda: ctapply([1, 2, 3, 4], [1, 1, 2, 2], lambda z, k: sum(z) + k, 10),
        expected["ct_dots"],
        named=True,
    )
    check(
        "ct_id",
        lambda: ctapply([1, 2, 3, 4], [1, 1, 2, 2], lambda z: z),
        expected["ct_id"],
        named=True,
    )
    check(
        "ct_named",
        lambda: ctapply([1, 2, 3], ["a", "a", "b"], lambda z: z),
        expected["ct_named"],
        named=True,
    )
    try:
        ctapply([1, 2, 3], [1, 1], sum)
    except ValueError as exc:
        assert str(exc) == "X and INDEX must have the same length"
    else:
        raise AssertionError("expected a length error")
    try:
        ctapply([1, 2], [True, False], sum)
    except ValueError as exc:
        assert str(exc) == "INDEX must be either integer, real or character vector"
    else:
        raise AssertionError("expected an index error")
    try:
        ctapply([1, 2], [1, 1], sum, merge=None)
    except TypeError as exc:
        assert str(exc) == "attempt to apply non-function"
    else:
        raise AssertionError("expected a merge error")
    print("ok")


if __name__ == "__main__":
    main()
