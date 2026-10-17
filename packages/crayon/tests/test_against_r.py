"""Compare crayon calls with the installed R package."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("R_LIBS_USER", str(Path.home() / "R" / "library"))

from crayon import (  # noqa: E402
    bgCyan,
    bgMagenta,
    black,
    blue,
    bold,
    chr,
    col_align,
    col_nchar,
    col_strsplit,
    col_substr,
    col_substring,
    combine_styles,
    concat,
    cyan,
    drop_style,
    finish,
    green,
    has_color,
    has_hyperlink,
    has_style,
    hyperlink,
    italic,
    magenta,
    make_style,
    num_ansi_colors,
    num_colors,
    options,
    red,
    reset,
    show_ansi_colors,
    silver,
    start,
    strip_style,
    style,
    styles,
    underline,
    white,
    yellow,
)

R_PRELUDE = r"""
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(crayon))
options(crayon.enabled = TRUE)
json_str <- function(s) {
  if (is.null(s)) return("null")
  if (length(s) == 1 && is.na(s)) return("null")
  s <- enc2utf8(as.character(s))
  bytes <- as.integer(charToRaw(s))
  parts <- character(length(bytes))
  for (i in seq_along(bytes)) {
    b <- bytes[[i]]
    parts[[i]] <- if (b == 34) paste0("\\", '"')
      else if (b == 92) paste0("\\", "\\")
      else if (b == 10) paste0("\\", "n")
      else if (b == 13) paste0("\\", "r")
      else if (b == 9) paste0("\\", "t")
      else if (b < 32 || b == 127) sprintf("\\u%04x", b)
      else intToUtf8(b)
  }
  paste0('"', paste(parts, collapse = ""), '"')
}
emit <- function(x) {
  if (is.list(x) && !is.data.frame(x)) {
    cat("[", paste(vapply(x, function(item) {
      if (length(item) == 1 && !is.list(item)) json_str(item)
      else paste0("[", paste(vapply(item, json_str, ""), collapse = ","), "]")
    }, ""), collapse = ","), "]\n", sep = "")
  } else if (length(x) > 1) {
    cat("[", paste(vapply(x, json_str, ""), collapse = ","), "]\n", sep = "")
  } else if (is.logical(x)) {
    cat(if (isTRUE(x)) "true" else "false", "\n")
  } else if (is.numeric(x)) {
    cat(sprintf("%.17g\n", x))
  } else {
    cat(json_str(x), "\n")
  }
}
"""


def r_value(body: str):
    script = R_PRELUDE + "\n" + body + "\n"
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout.strip().splitlines()[-1])


def setup_function(_fn=None):
    options(**{
        "crayon.enabled": True,
        "crayon.colors": None,
        "crayon.hyperlink": None,
        "cli.palette": None,
        "cli.num_colors": None,
        "width": 80,
    })


def test_concat_and_chr():
    assert concat("foo", "bar") == r_value('emit("foo" %+% "bar")')
    assert concat(["a", "b"], ["1", "2"]) == r_value('emit(c("a","b") %+% c("1","2"))')
    assert concat([], "*") == []
    assert chr(list(range(1, 11))) == [str(i) for i in range(1, 11)]
    assert chr(list(range(1, 11))) == r_value("emit(chr(1:10))")


def test_builtin_styles():
    assert red("Hello", "world!") == r_value('emit(red("Hello", "world!"))')
    assert red(["foo", "bar"]) == r_value('emit(red(c("foo", "bar")))')
    assert red(["foo", "bar"], "bar") == r_value('emit(red(c("foo", "bar"), "bar"))')
    assert bold("a") == r_value('emit(bold("a"))')
    assert reset("a") == r_value('emit(reset("a"))')
    assert silver("x") == r_value('emit(silver("x"))')
    assert underline(["foo", "bar"]) == r_value('emit(underline(c("foo","bar")))')
    nested = green(
        concat("I am a green line ", blue.underline.bold("with a blue substring"))
        + " that becomes green again!"
        if False
        else concat(
            concat("I am a green line ", blue.underline.bold("with a blue substring")),
            " that becomes green again!",
        )
    )
    assert nested == r_value(
        'emit(green("I am a green line " %+% blue$underline$bold("with a blue substring") %+% " that becomes green again!"))'
    )
    assert (yellow.bgMagenta.bold)("Hello world!") == r_value(
        'emit((yellow$bgMagenta$bold)("Hello world!"))'
    )
    assert red("multi-", underline("style"), sep="") == r_value(
        'emit(red("multi-", sep = "", underline("style")))'
    )
    assert (-red)("z") == r_value('emit((-red)("z"))')
    foobar = ["foo", "bar"]
    bigyo = ["bi", "gyo"]
    assert red(concat(concat(foobar, underline.bgBlue(bigyo)), "!")) == r_value(
        'emit(red(c("foo","bar") %+% underline$bgBlue(c("bi","gyo")) %+% "!"))'
    )


def test_make_style_and_registry():
    options(**{"crayon.enabled": True, "crayon.colors": 256})
    pink = make_style("pink", colors=256)
    assert pink("x") == r_value(
        'options(crayon.colors = 256L); emit(make_style("pink", colors = 256)("x"))'
    )
    pink8 = make_style("pink", colors=8)
    assert pink8("x") == r_value('emit(make_style("pink", colors = 8)("x"))')
    assert make_style("yellow3", colors=8)("x") == r_value(
        'emit(make_style("yellow3", colors = 8)("x"))'
    )
    options(**{"crayon.colors": None})
    made = make_style(probe="maroon", bg=True)
    assert "probe" in styles()
    assert made("q") == r_value(
        'options(crayon.enabled=TRUE); make_style(probe="maroon", bg=TRUE); emit(style("q", "probe")); drop_style("probe")'
    )
    drop_style("probe")
    assert "probe" not in styles()
    assert list(styles()) == r_value("emit(names(styles()))")


def test_style_combine_start():
    assert style("foobar", "bold") == r_value('emit(style("foobar", "bold"))')
    assert style("foobar", bold) == bold("foobar")
    alert = combine_styles(bold, red, bgCyan)
    assert alert("Warning!") == r_value('emit(combine_styles(bold, red, bgCyan)("Warning!"))')
    assert start(red) == r_value("emit(start(red))")
    assert finish(red) == r_value("emit(finish(red))")
    assert chr(red) == start(red)


def test_string_ops():
    sample = red("red") + " default " + green("green")
    r_sample = 'str <- paste(red("red"), "default", green("green"))'
    assert col_nchar(sample) == r_value(r_sample + "; emit(col_nchar(str))")
    assert col_substr(sample, 1, 5) == r_value(r_sample + "; emit(col_substr(str, 1, 5))")
    assert col_substr(sample, 3, 7) == r_value(r_sample + "; emit(col_substr(str, 3, 7))")
    assert col_substr("\033[31mred\033[39m", 1, 1) == r_value(
        'emit(col_substr("\033[31mred\033[39m", 1, 1))'
    )
    assert col_substr("foo\033[31mred\033[39m", 4, 4) == r_value(
        'emit(col_substr("foo\033[31mred\033[39m", 4, 4))'
    )
    assert col_substr("\033[31mred\033[39mfoo\033[31mred\033[39mbar", 7, 7) == r_value(
        'emit(col_substr("\033[31mred\033[39mfoo\033[31mred\033[39mbar", 7, 7))'
    )
    assert col_substr("red", 4, 5) == r_value('emit(col_substr("red", 4, 5))')
    assert col_substring(sample, 1, 15) == r_value(r_sample + "; emit(col_substring(str, 1, 15))")
    pieces = red("I am red---")
    pieces = concat(concat(red("I am red---"), green("and I am green-")), underline("I underlined"))
    got = col_strsplit(pieces, "[-]+")
    expect = r_value(
        's <- red("I am red---") %+% green("and I am green-") %+% underline("I underlined"); emit(col_strsplit(s, "[-]+"))'
    )
    assert got == expect
    assert col_strsplit(red("ab"), "") == r_value('emit(col_strsplit(red("ab"), ""))')
    assert col_align(red("foobar"), 20, "left") == r_value(
        'emit(col_align(red("foobar"), 20, "left"))'
    )
    assert col_align(red("foobar"), 20, "center") == r_value(
        'emit(col_align(red("foobar"), 20, "center"))'
    )
    assert col_align(red("foobar"), 20, "right") == r_value(
        'emit(col_align(red("foobar"), 20, "right"))'
    )
    assert strip_style(red("foobar")) == "foobar"
    assert has_style(red("foobar")) is True
    assert has_style("foobar") is False


def test_detection_and_link():
    options(**{"crayon.enabled": True, "crayon.colors": None})
    assert num_ansi_colors() == 8
    assert has_color() is True
    assert num_colors() == 8
    options(**{"crayon.colors": 256})
    assert num_colors() == 256
    assert num_ansi_colors() == 256
    options(**{"crayon.hyperlink": True})
    assert has_hyperlink() is True
    assert hyperlink("R", "https://r-project.org") == r_value(
        'options(crayon.hyperlink = TRUE); emit(hyperlink("R", "https://r-project.org"))'
    )
    options(**{"crayon.hyperlink": False})
    assert hyperlink("R", "https://r-project.org") == "R"


def test_palette_and_show(capsys):
    options(**{"crayon.enabled": True, "crayon.colors": 256, "cli.palette": "vscode"})
    assert red("a") == r_value(
        'options(crayon.enabled=TRUE, crayon.colors=256L, cli.palette="vscode"); emit(red("a"))'
    )
    assert silver("a") == r_value(
        'options(crayon.enabled=TRUE, crayon.colors=256L, cli.palette="vscode"); emit(silver("a"))'
    )
    assert bold("a") == r_value(
        'options(crayon.enabled=TRUE, crayon.colors=256L, cli.palette="vscode"); emit(bold("a"))'
    )
    options(**{"cli.palette": None, "crayon.colors": None, "width": 80})
    show_ansi_colors(8)
    printed = capsys.readouterr().out
    expect = subprocess.run(
        [
            "Rscript",
            "-e",
            '.libPaths(c(path.expand("~/R/library"), .libPaths())); suppressPackageStartupMessages(library(crayon)); options(crayon.enabled=TRUE, width=80); show_ansi_colors(8)',
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert expect.returncode == 0, expect.stderr
    assert printed == expect.stdout


def test_empty_and_errors():
    with pytest.raises(ValueError):
        concat(["a", "b"], ["c", "d", "e"])
    with pytest.raises(ValueError):
        red(["a", "b"], ["c", "d", "e"])
    assert col_substr([], 1, 1) == []
    assert concat("a", "b") == "ab"
