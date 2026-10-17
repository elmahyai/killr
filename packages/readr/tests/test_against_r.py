"""Compare readr 2.2.0 results with the Python translation."""

from __future__ import annotations

import os
import subprocess
import sys
import warnings
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
for extra in ("readr", "tibble", "withr", "stringi", "clipr"):
    path = str(REPO / "packages" / extra)
    if path not in sys.path:
        sys.path.insert(0, path)

warnings.simplefilter("ignore")

from readr import (  # noqa: E402
    I,
    AccumulateCallback,
    DataFrameCallback,
    as_col_spec,
    col_double,
    col_factor,
    cols,
    cols_only,
    count_fields,
    date_names_lang,
    date_names_langs,
    edition_get,
    format_csv,
    fwf_empty,
    fwf_widths,
    guess_encoding,
    guess_parser,
    locale,
    parse_date,
    parse_datetime,
    parse_double,
    parse_integer,
    parse_number,
    parse_time,
    problems,
    read_csv,
    read_csv2,
    read_csv_chunked,
    read_fwf,
    read_lines,
    read_log,
    read_table,
    readr_example,
    spec_csv,
    tokenizer_csv,
    type_convert,
    with_edition,
    write_csv,
)
from readr.parse import Hms  # noqa: E402
from readr.read import Table  # noqa: E402

R_SCRIPT = r"""
suppressPackageStartupMessages(library(readr))
options(readr.show_col_types = FALSE)
cell <- function(v) {
  if (length(v) == 0) return("")
  if (length(v) != 1) return(paste(vapply(v, cell, ""), collapse = "&"))
  if (inherits(v, "POSIXct")) return(format(v, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"))
  if (inherits(v, "Date")) return(format(v))
  if (inherits(v, "hms")) return(sprintf("%.17g", as.numeric(v)))
  if (is.factor(v)) return(paste0("F:", as.character(v), ":", paste(levels(v), collapse = "/")))
  if (is.logical(v)) return(if (is.na(v)) "NA" else if (v) "TRUE" else "FALSE")
  if (is.numeric(v)) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    if (is.infinite(v)) return(if (v > 0) "Inf" else "-Inf")
    return(sprintf("%.17g", v))
  }
  if (is.na(v)) return("NA")
  as.character(v)
}
flat <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.data.frame(x)) {
    bits <- paste(names(x), collapse = "|")
    for (col in x) bits <- paste0(bits, ";", paste(vapply(seq_along(col), function(i) cell(col[[i]]), ""), collapse = ","))
    pr <- problems(x)
    if (!is.null(pr) && nrow(pr) > 0) {
      bits <- paste0(bits, ";P:", paste(sprintf("%s/%s/%s/%s", pr$row, ifelse(is.na(pr$col), "NA", pr$col), pr$expected, pr$actual), collapse = ","))
    }
    return(bits)
  }
  if (length(x) == 0) return("")
  paste(vapply(seq_along(x), function(i) cell(x[[i]]), ""), collapse = ",")
}
esc <- function(s) {
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s
}
emit <- function(name, expr) {
  value <- tryCatch(expr, error = function(e) paste0("ERR:", conditionMessage(e)))
  text <- if (is.character(value) && length(value) == 1 && startsWith(value, "ERR:")) value else flat(value)
  cat(name, "\t", esc(text), "\n", sep = "")
}
ex <- function(name) readr_example(name)
emit("csv", read_csv(I("a,b\n1,2\n3,4")))
emit("repair", read_csv(I("x,x\n1,2"), name_repair = "unique_quiet"))
emit("problem", read_csv(I("x\n1\nb"), col_types = "d"))
emit("ed2", read_csv(I("1,2\n3,4,5"), col_names = c("X", "Y", "Z")))
emit("ed1", with_edition(1, read_csv(I("1,2\n3,4,5"), col_names = c("X", "Y", "Z"))))
emit("csv2", read_csv2(I("a;b\n1,5;2")))
emit("table", read_table(I("a b\n1 2\n3  4")))
emit("int", parse_integer(c("01", "2147483648", "3")))
emit("num", parse_number("$1,234.50"))
emit("time", parse_time(c("01:02:03", "1:02", "01:02:03.5")))
emit("date", parse_date(c("2020-01-02", "2020-02-31")))
emit("dttm", parse_datetime("2020-01-02 03:04:05-05:00"))
emit("lines", read_lines(I("a\n\nb\nNA"), na = "NA"))
emit("count", count_fields(I("1,2\n3,4,5\n\n6"), tokenizer_csv()))
emit("fwf", read_fwf(ex("fwf-sample.txt"), fwf_widths(c(20, 10, 12), c("name", "state", "ssn"))))
emit("log", read_log(ex("example.log"), n_max = 1))
emit("empty", paste(fwf_empty(ex("fwf-sample.txt"), col_names = c("name", "state", "ssn"))$begin, collapse = ","))
emit("enc", guess_encoding(ex("mtcars.csv"))$encoding)
emit("langs", length(date_names_langs()))
emit("edition", edition_get())
emit("locale", locale()$tz)
emit("spec", paste(vapply(spec_csv(I("x,y\n1,2\n3.5,a"))$cols, function(col) class(col)[1], ""), collapse = ","))
emit("guess", guess_parser(c("1", "2", "a")))
emit("write", format_csv(data.frame(a = c(1, 1/3, NA), b = c(TRUE, FALSE, NA), c = c("x", "a,b", NA))))
emit("mtcars", read_csv(ex("mtcars.csv"))$mpg[1])
emit("challenge", tail(read_csv(ex("challenge.csv"))$y, 1))
"""


def _cell(value) -> str:
    if value is None:
        return "NA"
    if isinstance(value, Hms):
        return format(value.seconds, ".17g")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if value != value:
            return "NaN"
        if value == float("inf"):
            return "Inf"
        if value == float("-inf"):
            return "-Inf"
        return format(value, ".17g")
    if isinstance(value, int):
        return str(value)
    return str(value)


def _flat_frame(frame) -> str:
    bits = "|".join(frame.names)
    for column in frame.columns:
        factor = getattr(column, "factor", None)
        if factor is not None:
            levels = "/".join("" if level is None else str(level) for level in factor.levels)
            cells = ",".join(
                "NA" if value is None else f"F:{value}:{levels}" for value in factor.values
            )
        else:
            cells = ",".join(_cell(value) for value in column)
        bits += ";" + cells
    found = list(getattr(frame, "problems", []) or [])
    if found:
        rendered = ",".join(
            f"{problem['row']}/{problem['col'] if problem['col'] is not None else 'NA'}/{problem['expected']}/{problem['actual']}"
            for problem in found
        )
        bits += ";P:" + rendered
    return bits


def _python_cases() -> dict[str, str]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        csv = read_csv(I("a,b\n1,2\n3,4"), show_col_types=False)
        repair = read_csv(I("x,x\n1,2"), name_repair="unique_quiet", show_col_types=False)
        problem = read_csv(I("x\n1\nb"), col_types="d", show_col_types=False)
        ed2 = read_csv(I("1,2\n3,4,5"), col_names=["X", "Y", "Z"], show_col_types=False)
        ed1 = with_edition(1, lambda: read_csv(I("1,2\n3,4,5"), col_names=["X", "Y", "Z"], show_col_types=False))
        csv2 = read_csv2(I("a;b\n1,5;2"), show_col_types=False)
        table = read_table(I("a b\n1 2\n3  4"), show_col_types=False)
        integers = parse_integer(["01", "2147483648", "3"])
        number = parse_number(["$1,234.50"])
        times = parse_time(["01:02:03", "1:02", "01:02:03.5"])
        dates = parse_date(["2020-01-02", "2020-02-31"])
        stamp = parse_datetime(["2020-01-02 03:04:05-05:00"])
        lines = read_lines(I("a\n\nb\nNA"), na=["NA"])
        counts = count_fields(I("1,2\n3,4,5\n\n6"), tokenizer_csv())
        fwf = read_fwf(
            readr_example("fwf-sample.txt"),
            fwf_widths([20, 10, 12], ["name", "state", "ssn"]),
            show_col_types=False,
        )
        log = read_log(readr_example("example.log"), n_max=1, show_col_types=False)
        empty = fwf_empty(readr_example("fwf-sample.txt"), col_names=["name", "state", "ssn"])
        encoding = guess_encoding(readr_example("mtcars.csv"))
        spec = spec_csv(I("x,y\n1,2\n3.5,a"))
        written = format_csv(
            Table(
                ["a", "b", "c"],
                [[1.0, 1 / 3, None], [True, False, None], ["x", "a,b", None]],
                3,
            )
        )
        cars = read_csv(readr_example("mtcars.csv"), show_col_types=False)
        challenge = read_csv(readr_example("challenge.csv"), show_col_types=False)
    return {
        "csv": _flat_frame(csv),
        "repair": _flat_frame(repair),
        "problem": _flat_frame(problem),
        "ed2": _flat_frame(ed2),
        "ed1": _flat_frame(ed1),
        "csv2": _flat_frame(csv2),
        "table": _flat_frame(table),
        "int": ",".join(_cell(value) for value in integers),
        "num": _cell(number[0]),
        "time": ",".join(_cell(value) for value in times),
        "date": ",".join(_cell(value) for value in dates),
        "dttm": _cell(stamp[0]),
        "lines": ",".join(_cell(value) for value in lines),
        "count": ",".join(str(value) for value in counts),
        "fwf": _flat_frame(fwf),
        "log": _flat_frame(log),
        "empty": ",".join(str(value) for value in empty["begin"]),
        "enc": encoding.columns[0][0],
        "langs": str(len(date_names_langs())),
        "edition": str(edition_get()),
        "locale": locale().tz,
        "spec": ",".join(f"collector_{collector.kind}" for collector in spec.cols),
        "guess": guess_parser(["1", "2", "a"]),
        "write": written,
        "mtcars": _cell(cars.columns[0][0]),
        "challenge": _cell(challenge.columns[1][-1]),
    }


def _r_cases() -> dict[str, str]:
    completed = subprocess.run(
        ["Rscript", "-e", R_SCRIPT],
        check=True,
        capture_output=True,
        text=True,
    )
    found = {}
    for line in completed.stdout.splitlines():
        if "\t" not in line:
            continue
        name, value = line.split("\t", 1)
        found[name] = (
            value.replace("\\\\", "\0").replace("\\n", "\n").replace("\\r", "\r").replace("\0", "\\")
        )
    return found


def test_matches_readr():
    python = _python_cases()
    origin = _r_cases()
    mismatches = []
    for name, value in python.items():
        other = origin.get(name)
        if value != other:
            mismatches.append(f"{name}\n  py {value!r}\n  r  {other!r}")
    assert not mismatches, "\n".join(mismatches)


def test_chunk_and_factor_helpers():
    frame = read_csv_chunked(
        readr_example("mtcars.csv"),
        DataFrameCallback(lambda data, pos: data),
        chunk_size=10,
    )
    assert frame.nrow == 32
    assert frame.columns[0][0] == 21.0
    total = read_csv_chunked(
        I("mpg\n1\n2\n3\n4"),
        AccumulateCallback(lambda data, pos, acc: acc + sum(data.columns[0]), acc=0),
        chunk_size=2,
        show_col_types=False,
    )
    assert total == 10
    factored = read_csv(
        I("a\nred\nblue"),
        col_types=cols(a=col_factor(["blue", "red"])),
        show_col_types=False,
    )
    assert list(factored.columns[0]) == ["red", "blue"]
    assert as_col_spec("dc").cols[0].kind == "double"
    assert cols_only(a=col_double()).default.kind == "skip"
    assert date_names_lang("en").mon[0] == "January"
    assert problems(read_csv(I("a\n1"), show_col_types=False)).nrow == 0
    path = Path(os.environ.get("TMPDIR", "/tmp")) / "readr-write-check.csv"
    write_csv(Table(["a"], [[1.0]], 1), path)
    assert path.read_text().startswith("a\n1\n")
    path.unlink()
