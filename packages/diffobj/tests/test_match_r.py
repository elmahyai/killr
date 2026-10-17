"""Checks against the installed diffobj 0.3.9."""

import os
import subprocess
import warnings

import pytest

from diffobj import (
    auto_context,
    console_lines,
    cont_f,
    diffobj_set_def_opts,
    div_f,
    gdo,
    make_blocking,
    nchar_html,
    pager_is_less,
    ses,
    ses_dat,
    span_f,
    tag_f,
)
from diffobj.options import settings

R_CASES = r"""
suppressPackageStartupMessages(library(diffobj))
enc_row <- function(dat) {
  op <- as.character(dat$op)
  val <- ifelse(is.na(dat$val), "NA", dat$val)
  if ("id.a" %in% names(dat)) {
    ida <- ifelse(is.na(dat$id.a), "NA", as.character(dat$id.a))
    idb <- ifelse(is.na(dat$id.b), "NA", as.character(dat$id.b))
    paste(op, val, ida, idb, sep = "|")
  } else paste(op, val, sep = "|")
}
show <- function(name, s, d) {
  cat("CASE ", name, "\n", sep = "")
  cat("SES ", paste(s, collapse = ","), "\n", sep = "")
  cat("DAT ", paste(enc_row(d), collapse = ";"), "\n", sep = "")
}
a <- letters[1:6]
b <- c("b", "CC", "DD", "d", "f")
show("letters", ses(a, b), ses_dat(a, b))
show("noextra", ses(a, b), ses_dat(a, b, extra = FALSE))
show("num", ses(1:3, c(1, 4)), ses_dat(1:3, c(1, 4)))
show("na", ses(c("a", NA), c("a", "b")), ses_dat(c("a", NA), c("a", "b")))
w <- tryCatch(
  ses(letters[1:10], LETTERS[1:10], max.diffs = 2),
  warning = function(e) conditionMessage(e)
)
cat("WARN ", w, "\n", sep = "")
"""


def _r(script: str) -> str:
    env = os.environ.copy()
    env["R_LIBS_USER"] = os.path.expanduser("~/R/library")
    return subprocess.check_output(["Rscript", "-e", script], text=True, env=env)


def _rows(rows):
    parts = []
    for row in rows:
        val = "NA" if row["val"] is None else str(row["val"])
        if "id_a" in row:
            ida = "NA" if row["id_a"] is None else str(row["id_a"])
            idb = "NA" if row["id_b"] is None else str(row["id_b"])
            parts.append("|".join([row["op"], val, ida, idb]))
        else:
            parts.append("|".join([row["op"], val]))
    return ";".join(parts)


def test_ses_matches_r():
    text = _r(R_CASES)
    found = {}
    warn = None
    name = None
    for line in text.splitlines():
        if line.startswith("CASE "):
            name = line[5:]
            found[name] = {}
        elif line.startswith("SES "):
            found[name]["ses"] = line[4:]
        elif line.startswith("DAT "):
            found[name]["dat"] = line[4:]
        elif line.startswith("WARN "):
            warn = line[5:]
    a = list("abcdef")
    b = ["b", "CC", "DD", "d", "f"]
    assert ",".join(ses(a, b)) == found["letters"]["ses"]
    assert _rows(ses_dat(a, b)) == found["letters"]["dat"]
    assert _rows(ses_dat(a, b, extra=False)) == found["noextra"]["dat"]
    assert ",".join(ses([1, 2, 3], [1, 4])) == found["num"]["ses"]
    assert _rows(ses_dat(["a", None], ["a", "b"])) == found["na"]["dat"]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ses(list("abcdefghij"), list("ABCDEFGHIJ"), max_diffs=2)
    assert caught
    assert str(caught[0].message) == warn


def test_tags_and_width_match_the_examples():
    letters = list("ABCDE")
    assert tag_f("div", "ex1")(letters) == [
        "<div class='ex1'>A</div>",
        "<div class='ex1'>B</div>",
        "<div class='ex1'>C</div>",
        "<div class='ex1'>D</div>",
        "<div class='ex1'>E</div>",
    ]
    styled = div_f("ex2", {"color": "green", "font-family": "arial"})(letters)
    assert styled[0] == "<div class='ex2' style='color: green; font-family: arial;'>A</div>"
    assert span_f("ex")(["A", "B"]) == ["<span class='ex'>A</span>", "<span class='ex'>B</span>"]
    assert cont_f()(letters) == (
        "<div class='diffobj-container'><pre class='diffobj-content'>ABCDE</pre></div>"
    )
    assert cont_f(["a", "b"])(["A", "B"]) == (
        "<div class='diffobj-container a b'><pre class='diffobj-content'>AB</pre></div>"
    )
    assert nchar_html("<a href='http:www.domain.com'>hello</a>") == 5
    assert nchar_html(["<b>ab</b>", "&amp;", "&AMP;", "a<br>b", ""]) == [2, 1, 5, 2, 0]


def test_options_context_and_pager():
    assert gdo("format") == "auto"
    assert gdo("max.diffs") == 50000
    assert gdo("align.threshold") == 0.25
    settings["diffobj.format"] = "raw"
    previous = diffobj_set_def_opts()
    assert previous["diffobj.format"] == "raw"
    assert gdo("format") == "auto"
    os.environ["LINES"] = "40"
    assert console_lines() == 40
    os.environ.pop("LINES", None)
    assert console_lines() == 48
    bounds = auto_context(0, 3)
    assert (bounds.min, bounds.max) == (0, 3)
    default = auto_context()
    assert (default.min, default.max) == (1, 10)
    with pytest.raises(ValueError, match="greater than zero"):
        auto_context(-1, 3)
    r_less = _r(
        'suppressPackageStartupMessages(library(diffobj)); cat(if (isTRUE(pager_is_less())) "TRUE" else "FALSE")'
    ).strip()
    assert pager_is_less() is (r_less == "TRUE")
    assert make_blocking(sum, invisible_res=False)(range(1, 11)) == 55
