"""Guide and trim indices checked against diffobj 0.3.9."""

import os
import subprocess

import pytest

from diffobj.guides import guidesChr, guidesDeparse, guidesFile, guidesPrint, guidesStr
from diffobj.trim import trimChr, trimDeparse, trimFile, trimPrint, trimStr, trim_sub

R = r"""
suppressPackageStartupMessages(library(diffobj))
pairs <- function(m) {
  if (!length(m)) return("[]")
  paste(apply(m, 1, function(r) paste(r[1], r[2], sep = ",")), collapse = " ")
}
idxs <- function(x) if (!length(x)) "[]" else paste(as.integer(x), collapse = ",")
show <- function(name, idx) cat("CASE ", name, "\n", idx, "\n", sep = "")

show("guidesChr", idxs(guidesChr(letters, c("a", "b"))))
show("trimChr", pairs(trimChr(c("a", "bb", ""), c("a", "bb", ""))))
show("trimLetters", pairs(trimChr(letters[1:3], letters[1:3])))

m <- matrix(10:12)
txt <- capture.output(m)
show("guidesPrint", idxs(guidesPrint(m, txt)))
show("trimPrint", pairs(trimPrint(m, txt)))
show("printLines", paste(encodeString(txt), collapse = "\n"))

m2 <- matrix(11:12)
txt2 <- capture.output(m2)
show("guidesPrint2", idxs(guidesPrint(m2, txt2)))
show("trimPrint2", pairs(trimPrint(m2, txt2)))

obj <- list(a = 1, b = list(c = 2))
s <- capture.output(str(obj))
show("guidesStr", idxs(guidesStr(obj, s)))
show("trimStr", pairs(trimStr(obj, s)))
show("strLines", paste(encodeString(s), collapse = "\n"))

err <- function(expr) tryCatch(expr, error = function(e) conditionMessage(e))
show("naGuide", err(guidesPrint(1:2, c("a", NA))))
show("naStr", err(guidesStr(1:2, c("a", NA))))
show("subLen", err(diffobj:::trim_sub(c("ab", "c"), c("a"))))
show("subStr", err(diffobj:::trim_sub("ab", "zz")))
"""


def _r(script: str) -> str:
    env = os.environ.copy()
    env["R_LIBS_USER"] = os.path.expanduser("~/R/library")
    return subprocess.check_output(["Rscript", "-e", script], text=True, env=env)


def _cases(text: str) -> dict[str, str]:
    found = {}
    name = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("CASE "):
            if name is not None:
                found[name] = "\n".join(buf)
            name = line[5:]
            buf = []
        else:
            buf.append(line)
    if name is not None:
        found[name] = "\n".join(buf)
    return found


def _pairs(text: str):
    if text == "[]":
        return []
    rows = []
    for item in text.split():
        start, end = item.split(",")
        end_v = None if end == "NA" else int(end)
        rows.append((int(start), end_v))
    return rows


def _idx(text: str):
    if text == "[]":
        return []
    return [int(item) for item in text.split(",")]


@pytest.fixture(scope="module")
def r_cases():
    return _cases(_r(R))


def test_guides_chr_is_empty(r_cases):
    assert guidesChr("anything", ["a", "b"]) == []
    assert guidesDeparse(None, ["a", "b"]) == []
    assert guidesFile(None, ["a", "b"]) == []
    assert _idx(r_cases["guidesChr"]) == []


def test_trim_chr_identity(r_cases):
    assert trimChr(None, ["a", "bb", ""]) == [(1, 1), (1, 2), (1, 0)]
    assert trimDeparse(None, ["a", "bb", ""]) == [(1, 1), (1, 2), (1, 0)]
    assert trimFile(None, ["a", "bb", ""]) == [(1, 1), (1, 2), (1, 0)]
    assert _pairs(r_cases["trimChr"]) == [(1, 1), (1, 2), (1, 0)]
    assert trimChr(list("abc"), list("abc")) == [(1, 1), (1, 1), (1, 1)]
    assert _pairs(r_cases["trimLetters"]) == [(1, 1), (1, 1), (1, 1)]
    assert trimChr(None, [None]) == [(1, None)]


def test_matrix_from_the_manual(r_cases):
    """``matrix(10:12)`` and ``matrix(11:12)`` from the trim manual."""

    lines = r_cases["printLines"].split("\n")
    matrix = type("Matrix", (), {"dim": (3, 1), "dimnames": None})()
    assert guidesPrint(["a", "b"], lines) == []
    assert guidesPrint(matrix, lines) == _idx(r_cases["guidesPrint"])
    assert trimPrint(matrix, lines) == _pairs(r_cases["trimPrint"])
    assert guidesPrint(matrix, lines) == [1]
    assert trimPrint(matrix, lines) == [(1, 9), (6, 9), (6, 9), (6, 9)]

    smaller = type("Matrix", (), {"dim": (2, 1), "dimnames": None})()
    # The second matrix in the same manual block is not reprinted here; its
    # indices were captured from the same R session.
    assert _idx(r_cases["guidesPrint2"]) == [1]
    assert _pairs(r_cases["trimPrint2"]) == [(1, 9), (6, 9), (6, 9)]
    assert trimPrint(smaller, ["     [,1]", "[1,]   11", "[2,]   12"]) == _pairs(
        r_cases["trimPrint2"]
    )


def test_str_guides_and_trim(r_cases):
    lines = r_cases["strLines"].split("\n")
    assert guidesStr({"a": 1}, lines) == _idx(r_cases["guidesStr"])
    assert trimStr({"a": 1}, lines) == _pairs(r_cases["trimStr"])


def test_r_error_text():
    with pytest.raises(ValueError, match=r"Cannot compute guides if `obj.as.chr` contains NAs"):
        guidesPrint(1, ["a", None])
    with pytest.raises(ValueError, match=r"Cannot compute guides if `obj.as.chr` contains NAs"):
        guidesStr(1, ["a", None])
    with pytest.raises(ValueError, match="same number of elements as original"):
        trim_sub(["ab", "c"], ["a"])
    with pytest.raises(ValueError, match="not a substring of orginal"):
        trim_sub(["ab"], ["zz"])


def test_error_text_matches_r(r_cases):
    assert r_cases["naGuide"] == "Cannot compute guides if `obj.as.chr` contains NAs"
    assert r_cases["naStr"] == "Cannot compute guides if `obj.as.chr` contains NAs"
    assert "same number of elements as original" in r_cases["subLen"]
    assert "not a substring of orginal" in r_cases["subStr"]
