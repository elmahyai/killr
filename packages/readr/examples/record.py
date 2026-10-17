"""Compare each readr export with R, then write the translation records."""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "output"
PROOF = ROOT / "proof"

ORDER = """
AccumulateCallback ChunkCallback DataFrameCallback ListCallback SideEffectChunkCallback
as.col_spec clipboard col_character col_date col_datetime col_double col_factor
col_guess col_integer col_logical col_number col_skip col_time cols cols_condense
cols_only count_fields datasource date_names date_names_lang date_names_langs
default_locale edition_get format_csv format_csv2 format_delim format_tsv
fwf_cols fwf_empty fwf_positions fwf_widths guess_encoding guess_parser
local_edition locale output_column parse_character parse_date parse_datetime
parse_double parse_factor parse_guess parse_integer parse_logical parse_number
parse_time parse_vector problems read_builtin read_csv read_csv2 read_csv2_chunked
read_csv_chunked read_delim read_delim_chunked read_file read_file_raw read_fwf
read_lines read_lines_chunked read_lines_raw read_lines_raw_chunked read_log
read_rds read_table read_tsv read_tsv_chunked readr_example readr_threads
should_read_lazy should_show_types show_progress spec spec_csv spec_csv2
spec_delim spec_table spec_tsv stop_for_problems tokenize tokenizer_csv
tokenizer_delim tokenizer_fwf tokenizer_line tokenizer_log tokenizer_tsv
tokenizer_ws type_convert with_edition write_csv write_csv2 write_delim
write_excel_csv write_excel_csv2 write_file write_lines write_rds write_tsv
""".split()

UNFINISHED = {}

PY_HEADER = '''
import json
import statistics
import tempfile
import time
import warnings
from datetime import date, datetime, timezone
from pathlib import Path

warnings.simplefilter("ignore")
from readr import *
from readr.parse import Factor, Hms
from readr.read import Table

def cell(value):
    if isinstance(value, Hms):
        return format(value.seconds, ".17g")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date) and not isinstance(value, datetime):
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
    if value is None:
        return "NA"
    return str(value)

def flatv(values):
    if isinstance(values, Factor):
        values = values.values
    if isinstance(values, (str, bytes)) or values is None:
        return cell(values)
    return ",".join(cell(value) for value in values)

def flatdf(frame):
    bits = "|".join(frame.names)
    for column in frame.columns:
        bits += ";" + flatv(column)
    return bits

def yn(value):
    return "TRUE" if bool(value) else "FALSE"

def frame(names, columns):
    return Table(list(names), [list(column) for column in columns], len(columns[0]) if columns else 0)
'''

R_HEADER = r"""
suppressPackageStartupMessages(library(readr))
options(readr.show_col_types = FALSE)
cell <- function(v) {
  if (length(v) == 0) return("")
  if (length(v) != 1) return(paste(vapply(v, cell, ""), collapse = "&"))
  if (inherits(v, "POSIXct")) return(format(v, "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"))
  if (inherits(v, "Date")) return(format(v))
  if (inherits(v, "hms")) return(sprintf("%.17g", as.numeric(v)))
  if (is.factor(v)) return(as.character(v))
  if (is.logical(v)) return(if (is.na(v)) "NA" else if (isTRUE(v)) "TRUE" else "FALSE")
  if (is.numeric(v)) {
    if (is.nan(v)) return("NaN")
    if (is.na(v)) return("NA")
    if (is.infinite(v)) return(if (v > 0) "Inf" else "-Inf")
    return(sprintf("%.17g", v))
  }
  if (is.na(v)) return("NA")
  as.character(v)
}
flatv <- function(x) {
  if (length(x) == 0) return("")
  paste(vapply(seq_along(x), function(i) cell(x[[i]]), ""), collapse = ",")
}
flatdf <- function(x) {
  bits <- paste(names(x), collapse = "|")
  for (col in x) bits <- paste0(bits, ";", flatv(col))
  bits
}
yn <- function(x) if (isTRUE(x)) "TRUE" else "FALSE"
"""

LOOP_PY = """
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
"""

LOOP_R = r"""
value <- one()
if (is.null(value)) value <- "NULL"
if (!is.character(value)) value <- as.character(value)
if (length(value) != 1) value <- paste(value, collapse = ",")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":\"%s\",\"median_ms\":%.17g}\n", gsub("\"", "\\\"", value), median(elapsed) * 1000))
"""


def case(name, python, title, desc, label, r, py, loads=None):
    return {
        "name": name,
        "python": python,
        "title": title,
        "desc": desc,
        "label": label,
        "r": textwrap.dedent(r).strip("\n"),
        "py": textwrap.dedent(py).strip("\n"),
        "loads": loads or [],
    }


CASES = [
    case("AccumulateCallback", "readr.callback.AccumulateCallback", "Accumulate chunks",
         "Adds each chunk into one running value.", "sum four rows in chunks of two",
         """
         sprintf("%.17g", read_csv_chunked(I("a\\n1\\n2\\n3\\n4"), AccumulateCallback$new(function(x, pos, acc) acc + sum(x$a), acc = 0), chunk_size = 2))
         """,
         """
         total = read_csv_chunked(I("a\\n1\\n2\\n3\\n4"), AccumulateCallback(lambda data, pos, acc: acc + sum(data.columns[0]), acc=0), chunk_size=2, show_col_types=False)
         return cell(total)
         """, ["tibble"]),
    case("ChunkCallback", "readr.callback.ChunkCallback", "Chunk callback base",
         "Receives each chunk and returns nothing.", "empty callback over two lines",
         """
         res <- read_lines_chunked(I("a\\nb"), ChunkCallback$new(function(x, pos) NULL), chunk_size = 1)
         if (is.null(res)) "NULL" else "OTHER"
         """,
         """
         res = read_lines_chunked(I("a\\nb"), ChunkCallback(lambda data, pos: None), chunk_size=1)
         return "NULL" if res is None else "OTHER"
         """),
    case("DataFrameCallback", "readr.callback.DataFrameCallback", "Row-bind chunk results",
         "Stacks the data frame returned from each chunk.", "three rows in chunks of two",
         """
         flatdf(read_csv_chunked(I("a,b\\n1,2\\n3,4\\n5,6"), DataFrameCallback$new(function(x, pos) x), chunk_size = 2))
         """,
         """
         return flatdf(read_csv_chunked(I("a,b\\n1,2\\n3,4\\n5,6"), DataFrameCallback(lambda data, pos: data), chunk_size=2, show_col_types=False))
         """, ["tibble"]),
    case("ListCallback", "readr.callback.ListCallback", "Collect chunk results in a list",
         "Keeps whatever each chunk callback returns.", "paste lines in chunks of two",
         """
         out <- read_lines_chunked(I("a\\nb\\nc"), ListCallback$new(function(x, pos) paste(x, collapse = ",")), chunk_size = 2)
         paste(unlist(out), collapse = ";")
         """,
         """
         out = read_lines_chunked(I("a\\nb\\nc"), ListCallback(lambda data, pos: ",".join(cell(v) for v in data.columns[0])), chunk_size=2)
         return ";".join(out)
         """),
    case("SideEffectChunkCallback", "readr.callback.SideEffectChunkCallback", "Callback for side effects",
         "Runs a function per chunk and discards its return value.", "count rows seen",
         """
         e <- new.env()
         e$n <- 0
         read_csv_chunked(I("a\\n1\\n2\\n3"), SideEffectChunkCallback$new(function(x, pos) { e$n <- e$n + nrow(x) }), chunk_size = 2)
         as.character(e$n)
         """,
         """
         seen = []
         def callback(data, pos):
             seen.append(data.nrow)
         read_csv_chunked(I("a\\n1\\n2\\n3"), SideEffectChunkCallback(callback), chunk_size=2, show_col_types=False)
         return str(sum(seen))
         """, ["tibble"]),
    case("as.col_spec", "readr.columns.as_col_spec", "Build a column specification",
         "A short string becomes one collector per letter.", "shortcut dc",
         """
         s <- as.col_spec("dc")
         paste(vapply(s$cols, function(col) class(col)[1], ""), collapse = ",")
         """,
         """
         spec = as_col_spec("dc")
         return ",".join("collector_" + collector.kind for collector in spec.cols)
         """),
    case("col_character", "readr.columns.col_character", "Character collector",
         "Keeps the field as text.", "class of col_character()",
         'class(col_character())[1]',
         'return "collector_" + col_character().kind'),
    case("col_date", "readr.columns.col_date", "Date collector",
         "Parses a date with an optional format.", "format %Y-%m-%d",
         """
         collector <- col_date(format = "%Y-%m-%d")
         paste(class(collector)[1], collector$format, sep = ";")
         """,
         """
         collector = col_date(format="%Y-%m-%d")
         return "collector_" + collector.kind + ";" + collector.fields["format"]
         """),
    case("col_datetime", "readr.columns.col_datetime", "Datetime collector",
         "Parses a date and time with an optional format.", "empty format",
         """
         collector <- col_datetime()
         paste(class(collector)[1], collector$format, sep = ";")
         """,
         """
         collector = col_datetime()
         return "collector_" + collector.kind + ";" + collector.fields["format"]
         """),
    case("col_double", "readr.columns.col_double", "Double collector",
         "Parses a field as a double.", "class of col_double()",
         'class(col_double())[1]',
         'return "collector_" + col_double().kind'),
    case("col_factor", "readr.columns.col_factor", "Factor collector",
         "Restricts values to a level set.", "ordered levels a and b",
         """
         collector <- col_factor(c("a", "b"), ordered = TRUE)
         paste(class(collector)[1], paste(collector$levels, collapse = ","), yn(collector$ordered), yn(collector$include_na), sep = ";")
         """,
         """
         collector = col_factor(["a", "b"], ordered=True)
         return "collector_" + collector.kind + ";" + ",".join(collector.fields["levels"]) + ";" + yn(collector.fields["ordered"]) + ";" + yn(collector.fields["include_na"])
         """),
    case("col_guess", "readr.columns.col_guess", "Guessing collector",
         "Lets the reader choose the type.", "class of col_guess()",
         'class(col_guess())[1]',
         'return "collector_" + col_guess().kind'),
    case("col_integer", "readr.columns.col_integer", "Integer collector",
         "Parses a field as a 32-bit integer.", "class of col_integer()",
         'class(col_integer())[1]',
         'return "collector_" + col_integer().kind'),
    case("col_logical", "readr.columns.col_logical", "Logical collector",
         "Parses the strict true and false spellings.", "class of col_logical()",
         'class(col_logical())[1]',
         'return "collector_" + col_logical().kind'),
    case("col_number", "readr.columns.col_number", "Number collector",
         "Parses a number that may contain a currency mark or grouping.", "class of col_number()",
         'class(col_number())[1]',
         'return "collector_" + col_number().kind'),
    case("col_skip", "readr.columns.col_skip", "Skipped collector",
         "Drops the column.", "class of col_skip()",
         'class(col_skip())[1]',
         'return "collector_" + col_skip().kind'),
    case("col_time", "readr.columns.col_time", "Time collector",
         "Parses a time of day.", "class of col_time()",
         'class(col_time())[1]',
         'return "collector_" + col_time().kind'),
    case("cols", "readr.columns.cols", "Named column specification",
         "Pairs column names with collectors. The default is a guess.", "double a and character b",
         """
         spec <- cols(a = col_double(), b = col_character())
         paste(c(paste(names(spec$cols), vapply(spec$cols, function(col) class(col)[1], ""), sep = "="), class(spec$default)[1]), collapse = ";")
         """,
         """
         spec = cols(a=col_double(), b=col_character())
         paired = ";".join(collector.fields["name"] + "=collector_" + collector.kind for collector in spec.cols)
         return paired + ";collector_" + spec.default.kind
         """),
    case("cols_condense", "readr.columns.cols_condense", "Drop the most common type",
         "The most common collector becomes the default. Ties use the alphabetically first kind.",
         "two doubles and one character",
         """
         condensed <- cols_condense(spec(read_csv(I("a,b,c\\n1,2,x\\n3,4,y"))))
         paste(paste(names(condensed$cols), collapse = ","), class(condensed$default)[1], class(condensed$cols[[1]])[1], sep = ";")
         """,
         """
         condensed = cols_condense(spec(read_csv(I("a,b,c\\n1,2,x\\n3,4,y"), show_col_types=False)))
         return ",".join(collector.fields.get("name", "") for collector in condensed.cols) + ";collector_" + condensed.default.kind + ";collector_" + condensed.cols[0].kind
         """),
    case("cols_only", "readr.columns.cols_only", "Read only named columns",
         "Every column that is not named is skipped.", "keep a",
         """
         spec <- cols_only(a = col_double())
         paste(class(spec$default)[1], names(spec$cols)[1], class(spec$cols[[1]])[1], sep = ";")
         """,
         """
         spec = cols_only(a=col_double())
         return "collector_" + spec.default.kind + ";" + spec.cols[0].fields["name"] + ";collector_" + spec.cols[0].kind
         """),
    case("count_fields", "readr.read.count_fields", "Count fields per record",
         "Uses the tokenizer, and a csv tokenizer skips a blank line.", "three records",
         """
         paste(count_fields(I("1,2\\n3,4,5\\n\\n6"), tokenizer_csv()), collapse = ",")
         """,
         """
         return ",".join(str(value) for value in count_fields(I("1,2\\n3,4,5\\n\\n6"), tokenizer_csv()))
         """),
    case("datasource", "readr.datasource", "Describe an input source",
         "Records skip, comments, and whether blank rows are ignored. The default keeps blank rows.",
         "literal data with skip 2",
         """
         source <- datasource(I("a\\n1"), skip = 2, comment = "#")
         paste(source$skip, yn(source$skip_empty_rows), source$comment, yn(source$skip_quote), sep = ";")
         """,
         """
         source = datasource(I("a\\n1"), skip=2, comment="#")
         return str(source["skip"]) + ";" + yn(source["skip_empty_rows"]) + ";" + source["comment"] + ";" + yn(source["skip_quote"])
         """),
    case("date_names", "readr.locale.date_names", "Custom date names",
         "Stores month names, weekday names, and the AM/PM marks. Weekdays start on Sunday.",
         "one English month and Sunday",
         """
         names <- date_names(month.name, month.abb, c("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"), c("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"))
         paste(names$mon[1], names$mon_ab[1], names$day[1], names$day_ab[1], sep = ";")
         """,
         """
         months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
         short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
         days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
         day_ab = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
         names = date_names(months, short, days, day_ab)
         return names.mon[0] + ";" + names.mon_ab[0] + ";" + names.day[0] + ";" + names.day_ab[0]
         """),
    case("date_names_lang", "readr.locale.date_names_lang", "Date names for a language",
         "Looks up the ICU date symbols shipped with readr.", "English January and Sunday",
         """
         names <- date_names_lang("en")
         paste(names$mon[1], names$day[1], sep = ";")
         """,
         """
         names = date_names_lang("en")
         return names.mon[0] + ";" + names.day[0]
         """),
    case("date_names_langs", "readr.locale.date_names_langs", "Known date-name languages",
         "Lists the language codes in the bundled symbol table.", "how many languages",
         'as.character(length(date_names_langs()))',
         'return str(len(date_names_langs()))'),
    case("default_locale", "readr.locale.default_locale", "Session locale",
         "The locale stored in the readr.default_locale option. The default is US English, UTF-8, and UTC.",
         "decimal mark, zone, and encoding",
         """
         loc <- default_locale()
         paste(loc$decimal_mark, loc$tz, loc$encoding, sep = ";")
         """,
         """
         loc = default_locale()
         return loc.decimal_mark + ";" + loc.tz + ";" + loc.encoding
         """, ["withr"]),
    case("edition_get", "readr.runtime.edition_get", "Active readr edition",
         "Edition 2 is the default outside a package that asks for edition 1.", "current edition",
         'as.character(edition_get())',
         'return str(edition_get())', ["withr"]),
    case("format_csv", "readr.write.format_csv", "Format a data frame as CSV",
         "Doubles use the short grisu3 form. A comma inside a field is quoted.", "one third and a comma",
         """
         format_csv(data.frame(a = c(1, 1/3, NA), b = c(TRUE, FALSE, NA), c = c("x", "a,b", NA)))
         """,
         """
         return format_csv(frame(["a", "b", "c"], [[1.0, 1/3, None], [True, False, None], ["x", "a,b", None]]))
         """, ["tibble"]),
    case("format_csv2", "readr.write.format_csv2", "Format a data frame as European CSV",
         "The decimal mark is a comma and the field separator is a semicolon.", "1.5",
         'format_csv2(data.frame(a = c(1.5, NA)))',
         'return format_csv2(frame(["a"], [[1.5, None]]))', ["tibble"]),
    case("format_delim", "readr.write.format_delim", "Format a data frame with a delimiter",
         "Writes a header and a trailing newline. Missing values are bare NA.", "pipe delimiter",
         'format_delim(data.frame(a = c(1, NA)), delim = "|")',
         'return format_delim(frame(["a"], [[1.0, None]]), delim="|")', ["tibble"]),
    case("format_tsv", "readr.write.format_tsv", "Format a data frame as TSV",
         "Fields are separated by a tab.", "two columns",
         'format_tsv(data.frame(a = 1, b = "x"))',
         'return format_tsv(frame(["a", "b"], [[1.0], ["x"]]))', ["tibble"]),
    case("fwf_cols", "readr.read.fwf_cols", "Named fixed widths",
         "Names are the column names and the values are widths.", "name 20 and state 10",
         """
         spec <- fwf_cols(name = 20, state = 10)
         paste(paste(spec$begin, collapse = ","), paste(spec$end, collapse = ","), paste(spec$col_names, collapse = ","), sep = ";")
         """,
         """
         spec = fwf_cols(name=20, state=10)
         end = ",".join("NA" if value is None else str(value) for value in spec["end"])
         return ",".join(str(value) for value in spec["begin"]) + ";" + end + ";" + ",".join(spec["col_names"])
         """),
    case("fwf_empty", "readr.read.fwf_empty", "Guess fixed-width positions",
         "A run of two spaces ends a field. The last end is missing so the field runs to the end of the line.",
         "fwf-sample.txt with three names",
         """
         spec <- fwf_empty(readr_example("fwf-sample.txt"), col_names = c("name", "state", "ssn"))
         paste(paste(spec$begin, collapse = ","), paste(ifelse(is.na(spec$end), "NA", spec$end), collapse = ","), paste(spec$col_names, collapse = ","), sep = ";")
         """,
         """
         spec = fwf_empty(readr_example("fwf-sample.txt"), col_names=["name", "state", "ssn"])
         end = ",".join("NA" if value is None else str(value) for value in spec["end"])
         return ",".join(str(value) for value in spec["begin"]) + ";" + end + ";" + ",".join(spec["col_names"])
         """),
    case("fwf_positions", "readr.read.fwf_positions", "Fixed-width positions",
         "Start and end are 1-based and the end is inclusive.", "columns at 1-20 and 21-30",
         """
         spec <- fwf_positions(c(1, 21), c(20, 30), c("name", "state"))
         paste(paste(spec$begin, collapse = ","), paste(spec$end, collapse = ","), paste(spec$col_names, collapse = ","), sep = ";")
         """,
         """
         spec = fwf_positions([1, 21], [20, 30], ["name", "state"])
         end = ",".join("NA" if value is None else str(value) for value in spec["end"])
         return ",".join(str(value) for value in spec["begin"]) + ";" + end + ";" + ",".join(spec["col_names"])
         """),
    case("fwf_widths", "readr.read.fwf_widths", "Fixed widths",
         "Widths are measured from the start of the line.", "20, 10, and 12",
         """
         spec <- fwf_widths(c(20, 10, 12), c("name", "state", "ssn"))
         paste(paste(spec$begin, collapse = ","), paste(spec$end, collapse = ","), paste(spec$col_names, collapse = ","), sep = ";")
         """,
         """
         spec = fwf_widths([20, 10, 12], ["name", "state", "ssn"])
         end = ",".join("NA" if value is None else str(value) for value in spec["end"])
         return ",".join(str(value) for value in spec["begin"]) + ";" + end + ";" + ",".join(spec["col_names"])
         """),
    case("guess_encoding", "readr.guess_encoding", "Guess a file encoding",
         "ASCII input is reported as ASCII with confidence 1. Other input uses stringi and keeps encodings above the threshold.",
         "mtcars.csv",
         """
         guessed <- guess_encoding(readr_example("mtcars.csv"))
         paste(paste(guessed$encoding, sprintf("%.17g", guessed$confidence), sep = "="), collapse = ",")
         """,
         """
         guessed = guess_encoding(readr_example("mtcars.csv"))
         return ",".join(encoding + "=" + format(confidence, ".17g") for encoding, confidence in zip(guessed.columns[0], guessed.columns[1]))
         """, ["stringi", "tibble"]),
    case("guess_parser", "readr.parse.guess_parser", "Guess a column type",
         "Edition 2 guesses double, never integer. A mixed column stays character.", "numbers and a letter",
         'guess_parser(c("1", "2", "a"))',
         'return guess_parser(["1", "2", "a"])'),
    case("local_edition", "readr.runtime.local_edition", "Edition for the current block",
         "The edition lasts until the surrounding function or with-block ends.", "edition 1 inside a function",
         """
         inside <- function() { local_edition(1); as.character(edition_get()) }
         paste(inside(), edition_get())
         """,
         """
         def inside():
             with local_edition(1):
                 return edition_get()
         return str(inside()) + " " + str(edition_get())
         """, ["withr"]),
    case("locale", "readr.locale.locale", "Decimal marks and time zone",
         "The default locale is UTF-8 and UTC. The decimal mark and the grouping mark must differ.",
         "comma decimals in UTC",
         """
         loc <- locale(decimal_mark = ",", grouping_mark = ".", tz = "UTC")
         paste(loc$decimal_mark, loc$grouping_mark, loc$tz, loc$encoding, loc$date_names$mon[1], sep = ";")
         """,
         """
         loc = locale(decimal_mark=",", grouping_mark=".", tz="UTC")
         return loc.decimal_mark + ";" + loc.grouping_mark + ";" + loc.tz + ";" + loc.encoding + ";" + loc.date_names.mon[0]
         """),
    case("output_column", "readr.write.output_column", "Coerce a column for writing",
         "A datetime is written in UTC as ISO-8601 with a trailing Z.", "2016-01-01 UTC",
         """
         output_column(as.POSIXct("2016-01-01 00:00:00", tz = "UTC"), "when")
         """,
         """
         return output_column(datetime(2016, 1, 1, tzinfo=timezone.utc), "when")
         """),
    case("parse_character", "readr.parse.parse_character", "Parse character",
         "Trims whitespace and turns the missing-value strings into NA.", "NA and spaced text",
         'flatv(parse_character(c(" NA ", "x")))',
         'return flatv(parse_character([" NA ", "x"]))'),
    case("parse_date", "readr.parse.parse_date", "Parse dates",
         "The default format is a calendar date. A day that is not on the calendar is missing.",
         "2 January and 31 February",
         'flatv(parse_date(c("2020-01-02", "2020-02-31")))',
         'return flatv(parse_date(["2020-01-02", "2020-02-31"]))'),
    case("parse_datetime", "readr.parse.parse_datetime", "Parse datetimes",
         "An offset is converted to UTC.", "05:00 behind UTC",
         'flatv(parse_datetime("2020-01-02 03:04:05-05:00"))',
         'return flatv(parse_datetime(["2020-01-02 03:04:05-05:00"]))'),
    case("parse_double", "readr.parse.parse_double", "Parse doubles",
         "A trailing letter is a failed double, not a partial number.", "1.5 and 1a",
         'flatv(parse_double(c("1.5", "1a")))',
         'return flatv(parse_double(["1.5", "1a"]))'),
    case("parse_factor", "readr.parse.parse_factor", "Parse factors",
         "Known levels stay in the given order. Anything else is missing.", "blue then red",
         """
         parsed <- parse_factor(c("red", "blue", "green"), levels = c("blue", "red"))
         paste(flatv(as.character(parsed)), paste(levels(parsed), collapse = "/"), sep = ";")
         """,
         """
         parsed = parse_factor(["red", "blue", "green"], levels=["blue", "red"])
         return flatv(parsed) + ";" + "/".join(parsed.factor.levels)
         """),
    case("parse_guess", "readr.parse.parse_guess", "Parse by guessing",
         "A column of whole numbers is parsed as double.", "1, 2, and 3",
         'flatv(parse_guess(c("1", "2", "3")))',
         'return flatv(parse_guess(["1", "2", "3"]))'),
    case("parse_integer", "readr.parse.parse_integer", "Parse 32-bit integers",
         "Leading zeros are accepted. A value past the 32-bit range is missing.", "01 and 2147483648",
         'flatv(parse_integer(c("01", "2147483648", "3")))',
         'return flatv(parse_integer(["01", "2147483648", "3"]))'),
    case("parse_logical", "readr.parse.parse_logical", "Parse logical values",
         "Accepts T, F, TRUE, and FALSE in either case. The digits 1 and 0 are not logical.",
         "T, F, and 1",
         'flatv(parse_logical(c("T", "F", "1")))',
         'return flatv(parse_logical(["T", "F", "1"]))'),
    case("parse_number", "readr.parse.parse_number", "Parse numbers with marks",
         "A currency sign and grouping marks are removed before the number is read.", "dollar amount",
         'flatv(parse_number("$1,234.50"))',
         'return flatv(parse_number(["$1,234.50"]))'),
    case("parse_time", "readr.parse.parse_time", "Parse times of day",
         "The result is seconds since midnight. A fractional second on an hours-minutes-seconds time is dropped.",
         "01:02:03 and a fraction",
         'flatv(parse_time(c("01:02:03", "1:02", "01:02:03.5")))',
         'return flatv(parse_time(["01:02:03", "1:02", "01:02:03.5"]))'),
    case("parse_vector", "readr.parse.parse_vector", "Parse with one collector",
         "Applies one collector to a character vector and records problems on the result.",
         "doubles with one failure",
         'flatv(parse_vector(c("1", "2", "x"), col_double()))',
         'return flatv(parse_vector(["1", "2", "x"], col_double()))'),
    case("problems", "readr.read.problems", "Parsing problems",
         "Each problem has a row, a column, the expected type, and the text that failed.",
         "a letter in a double column",
         """
         parsed <- read_csv(I("x\\n1\\nb"), col_types = "d")
         found <- problems(parsed)
         paste(paste(found$row, found$col, found$expected, found$actual, sep = "/"), collapse = ",")
         """,
         """
         parsed = read_csv(I("x\\n1\\nb"), col_types="d", show_col_types=False)
         found = problems(parsed)
         return ",".join(str(row) + "/" + ("NA" if col is None else str(col)) + "/" + expected + "/" + actual for row, col, expected, actual in zip(found.columns[0], found.columns[1], found.columns[2], found.columns[3]))
         """, ["tibble"]),
    case("read_csv", "readr.read.read_csv", "Read comma-separated values",
         "Edition 2 guesses doubles. Repeated names are repaired so every copy gets a position suffix.",
         "repeated column name x",
         'flatdf(read_csv(I("x,x\\n1,2\\n3,4"), name_repair = "unique_quiet"))',
         'return flatdf(read_csv(I("x,x\\n1,2\\n3,4"), name_repair="unique_quiet", show_col_types=False))',
         ["tibble"]),
    case("read_csv2", "readr.read.read_csv2", "Read semicolon-separated values",
         "A comma is the decimal mark. When the decimal mark is already a dot, readr switches and says so.",
         "1,5 and 2",
         'flatdf(read_csv2(I("a;b\\n1,5;2")))',
         'return flatdf(read_csv2(I("a;b\\n1,5;2"), show_col_types=False))', ["tibble"]),
    case("read_csv2_chunked", "readr.callback.read_csv2_chunked", "Read European CSV in chunks",
         "The chunks are read with the edition 2 parser and then handed to the callback.",
         "two chunks of one row",
         """
         flatdf(read_csv2_chunked(I("a;b\\n1,5;2\\n3;4"), DataFrameCallback$new(function(x, pos) x), chunk_size = 1))
         """,
         """
         return flatdf(read_csv2_chunked(I("a;b\\n1,5;2\\n3;4"), DataFrameCallback(lambda data, pos: data), chunk_size=1, show_col_types=False))
         """, ["tibble"]),
    case("read_csv_chunked", "readr.callback.read_csv_chunked", "Read CSV in chunks",
         "The callback sees each chunk. A data-frame callback stacks them.", "chunk size 2",
         """
         flatdf(read_csv_chunked(I("a\\n1\\n2\\n3\\n4"), DataFrameCallback$new(function(x, pos) x), chunk_size = 2))
         """,
         """
         return flatdf(read_csv_chunked(I("a\\n1\\n2\\n3\\n4"), DataFrameCallback(lambda data, pos: data), chunk_size=2, show_col_types=False))
         """, ["tibble"]),
    case("read_delim", "readr.read.read_delim", "Read a delimited file",
         "Edition 2 takes the width from the first record and glues extra fields into the last column.",
         "a short first row",
         'flatdf(read_delim(I("1,2\\n3,4,5"), delim = ",", col_names = c("X", "Y", "Z")))',
         'return flatdf(read_delim(I("1,2\\n3,4,5"), delim=",", col_names=["X", "Y", "Z"], show_col_types=False))',
         ["tibble"]),
    case("read_delim_chunked", "readr.callback.read_delim_chunked", "Read a delimiter in chunks",
         "Same parser as read_delim, then the callback.", "pipe delimiter",
         """
         flatdf(read_delim_chunked(I("a|b\\n1|2\\n3|4"), DataFrameCallback$new(function(x, pos) x), delim = "|", chunk_size = 2))
         """,
         """
         return flatdf(read_delim_chunked(I("a|b\\n1|2\\n3|4"), DataFrameCallback(lambda data, pos: data), delim="|", chunk_size=2, show_col_types=False))
         """, ["tibble"]),
    case("read_file", "readr.lines.read_file", "Read a whole file",
         "Returns one string, line endings included.", "two lines",
         'read_file(I("a\\nb\\n"))',
         'return read_file(I("a\\nb\\n"))'),
    case("read_file_raw", "readr.lines.read_file_raw", "Read a file as bytes",
         "Returns one byte per character of the input.", "ab",
         'paste(as.integer(read_file_raw(I("ab"))), collapse = ",")',
         'return ",".join(str(value) for value in read_file_raw(I("ab")))'),
    case("read_fwf", "readr.read.read_fwf", "Read fixed-width fields",
         "Widths are trimmed when trim_ws is true.", "fwf-sample.txt",
         """
         parsed <- read_fwf(readr_example("fwf-sample.txt"), fwf_widths(c(20, 10, 12), c("name", "state", "ssn")))
         paste(parsed$name[1], parsed$state[1], parsed$ssn[1], sep = "|")
         """,
         """
         parsed = read_fwf(readr_example("fwf-sample.txt"), fwf_widths([20, 10, 12], ["name", "state", "ssn"]), show_col_types=False)
         return str(parsed.columns[0][0]) + "|" + str(parsed.columns[1][0]) + "|" + str(parsed.columns[2][0])
         """, ["tibble"]),
    case("read_lines", "readr.lines.read_lines", "Read lines",
         "The default does not treat the text NA as missing. An empty line stays empty.",
         "NA as a missing line",
         """
         lines <- read_lines(I("a\\n\\nb\\nNA"), na = "NA")
         paste(ifelse(is.na(lines), "NA", lines), collapse = ",")
         """,
         """
         return flatv(read_lines(I("a\\n\\nb\\nNA"), na=["NA"]))
         """),
    case("read_lines_chunked", "readr.lines.read_lines_chunked", "Read lines in chunks",
         "Each chunk is a small table with one character column.", "chunks of two",
         """
         out <- read_lines_chunked(I("a\\nb\\nc"), ListCallback$new(function(x, pos) paste(x, collapse = ",")), chunk_size = 2)
         paste(unlist(out), collapse = ";")
         """,
         """
         out = read_lines_chunked(I("a\\nb\\nc"), ListCallback(lambda data, pos: ",".join(cell(v) for v in data.columns[0])), chunk_size=2)
         return ";".join(out)
         """),
    case("read_lines_raw", "readr.lines.read_lines_raw", "Read lines as bytes",
         "Each line is a vector of byte values, without the line ending.", "ab and cd",
         """
         lines <- read_lines_raw(I("ab\\ncd"))
         paste(paste(as.integer(lines[[1]]), collapse = ","), paste(as.integer(lines[[2]]), collapse = ","), sep = ";")
         """,
         """
         lines = read_lines_raw(I("ab\\ncd"))
         return ";".join(",".join(str(value) for value in line) for line in lines)
         """),
    case("read_lines_raw_chunked", "readr.lines.read_lines_raw_chunked", "Read raw lines in chunks",
         "Each chunk holds raw lines. This check reports the length of the first line in each chunk.",
         "chunks of two",
         """
         out <- read_lines_raw_chunked(I("ab\\ncd\\nef"), ListCallback$new(function(x, pos) length(x[[1]])), chunk_size = 2)
         paste(unlist(out), collapse = ",")
         """,
         """
         out = read_lines_raw_chunked(I("ab\\ncd\\nef"), ListCallback(lambda data, pos: len(data.columns[0][0])), chunk_size=2)
         return ",".join(str(value) for value in out)
         """),
    case("read_log", "readr.read.read_log", "Read a web log",
         "A hyphen is missing. Names are X1 onward because the file has no header.", "first example line",
         """
         parsed <- read_log(readr_example("example.log"), n_max = 1)
         paste(paste(names(parsed), collapse = ","), flatv(parsed[[1]]), yn(is.na(parsed[[2]])), as.character(parsed[[3]]), flatv(parsed[[6]]), flatv(parsed[[7]]), sep = "|")
         """,
         """
         parsed = read_log(readr_example("example.log"), n_max=1, show_col_types=False)
         return ",".join(parsed.names) + "|" + flatv(parsed.columns[0]) + "|" + yn(parsed.columns[1][0] is None) + "|" + str(parsed.columns[2][0]) + "|" + flatv(parsed.columns[5]) + "|" + flatv(parsed.columns[6])
         """, ["tibble"]),
    case("read_table", "readr.read.read_table", "Read whitespace-separated columns",
         "One or more spaces separate fields.", "two spaces between 3 and 4",
         'flatdf(read_table(I("a b\\n1 2\\n3  4")))',
         'return flatdf(read_table(I("a b\\n1 2\\n3  4"), show_col_types=False))', ["tibble"]),
    case("read_tsv", "readr.read.read_tsv", "Read tab-separated values",
         "The delimiter is a tab. Types are guessed the same way as read_csv.", "two rows",
         'flatdf(read_tsv(I("a\\tb\\n1\\t2\\n3\\t4")))',
         'return flatdf(read_tsv(I("a\\tb\\n1\\t2\\n3\\t4"), show_col_types=False))', ["tibble"]),
    case("read_tsv_chunked", "readr.callback.read_tsv_chunked", "Read TSV in chunks",
         "The chunks use the tab delimiter.", "chunk size 1",
         """
         flatdf(read_tsv_chunked(I("a\\tb\\n1\\t2\\n3\\t4"), DataFrameCallback$new(function(x, pos) x), chunk_size = 1))
         """,
         """
         return flatdf(read_tsv_chunked(I("a\\tb\\n1\\t2\\n3\\t4"), DataFrameCallback(lambda data, pos: data), chunk_size=1, show_col_types=False))
         """, ["tibble"]),
    case("readr_example", "readr.runtime.readr_example", "Path to a bundled example",
         "The examples are the files shipped in inst/extdata.", "mtcars.csv",
         'basename(readr_example("mtcars.csv"))',
         'return Path(readr_example("mtcars.csv")).name'),
    case("readr_threads", "readr.runtime.readr_threads", "Thread count",
         "The option readr.num_threads wins. Otherwise the VROOM_THREADS environment variable, then the CPU count.",
         "option set to 4",
         """
         old <- options(readr.num_threads = 4)
         on.exit(options(old), add = TRUE)
         as.character(readr_threads())
         """,
         """
         from withr._options import options as set_options
         set_options(**{"readr.num_threads": 4})
         try:
             return str(readr_threads())
         finally:
             set_options(**{"readr.num_threads": None})
         """, ["withr"]),
    case("should_read_lazy", "readr.runtime.should_read_lazy", "Whether reads should be lazy",
         "The default is eager. The option readr.read_lazy asks for a lazy read.", "option TRUE",
         """
         old <- options(readr.read_lazy = TRUE)
         on.exit(options(old), add = TRUE)
         yn(should_read_lazy())
         """,
         """
         from withr._options import options as set_options
         set_options(**{"readr.read_lazy": True})
         try:
             return yn(should_read_lazy())
         finally:
             set_options(**{"readr.read_lazy": None})
         """, ["withr"]),
    case("should_show_types", "readr.runtime.should_show_types", "Whether to show column types",
         "TRUE and FALSE follow the option. An unset option leaves the decision to the caller.",
         "option TRUE then FALSE",
         """
         old <- options(readr.show_col_types = TRUE)
         on.exit(options(old), add = TRUE)
         first <- yn(should_show_types())
         options(readr.show_col_types = FALSE)
         paste(first, yn(should_show_types()))
         """,
         """
         from withr._options import options as set_options
         set_options(**{"readr.show_col_types": True})
         first = yn(should_show_types())
         set_options(**{"readr.show_col_types": False})
         try:
             return first + " " + yn(should_show_types())
         finally:
             set_options(**{"readr.show_col_types": False})
         """, ["withr"]),
    case("show_progress", "readr.runtime.show_progress", "Whether to show a progress bar",
         "Progress is off unless the option is TRUE and the session is interactive.",
         "this non-interactive session",
         'yn(show_progress())',
         'return yn(show_progress())', ["withr"]),
    case("spec", "readr.read.spec", "Column specification of a data frame",
         "The specification is stored on the data frame returned by a reader.", "1 and x",
         """
         parsed <- spec(read_csv(I("a,b\\n1,x")))
         paste(vapply(parsed$cols, function(col) class(col)[1], ""), collapse = ",")
         """,
         """
         parsed = spec(read_csv(I("a,b\\n1,x"), show_col_types=False))
         return ",".join("collector_" + collector.kind for collector in parsed.cols)
         """),
    case("spec_csv", "readr.read.spec_csv", "Guess a CSV specification",
         "Guesses from the file without returning the rows. Edition 1 guessing is forced for spec helpers.",
         "a double and a character",
         """
         parsed <- spec_csv(I("x,y\\n1,2\\n3.5,a"))
         paste(vapply(parsed$cols, function(col) class(col)[1], ""), collapse = ",")
         """,
         """
         parsed = spec_csv(I("x,y\\n1,2\\n3.5,a"))
         return ",".join("collector_" + collector.kind for collector in parsed.cols)
         """),
    case("spec_csv2", "readr.read.spec_csv2", "Guess a European CSV specification",
         "Uses a semicolon and a comma decimal mark.", "1,5 and a letter",
         """
         parsed <- spec_csv2(I("x;y\\n1,5;a"))
         paste(vapply(parsed$cols, function(col) class(col)[1], ""), collapse = ",")
         """,
         """
         parsed = spec_csv2(I("x;y\\n1,5;a"))
         return ",".join("collector_" + collector.kind for collector in parsed.cols)
         """),
    case("spec_delim", "readr.read.spec_delim", "Guess a delimited specification",
         "The delimiter is the one you pass.", "pipe delimiter",
         """
         parsed <- spec_delim(I("x|y\\n1|a"), delim = "|")
         paste(vapply(parsed$cols, function(col) class(col)[1], ""), collapse = ",")
         """,
         """
         parsed = spec_delim(I("x|y\\n1|a"), delim="|")
         return ",".join("collector_" + collector.kind for collector in parsed.cols)
         """),
    case("spec_table", "readr.read.spec_table", "Guess a whitespace specification",
         "Columns are separated by spaces.", "1 and a",
         """
         parsed <- spec_table(I("x y\\n1 a"))
         paste(vapply(parsed$cols, function(col) class(col)[1], ""), collapse = ",")
         """,
         """
         parsed = spec_table(I("x y\\n1 a"))
         return ",".join("collector_" + collector.kind for collector in parsed.cols)
         """),
    case("spec_tsv", "readr.read.spec_tsv", "Guess a TSV specification",
         "The delimiter is a tab.", "1 and a",
         """
         parsed <- spec_tsv(I("x\\ty\\n1\\ta"))
         paste(vapply(parsed$cols, function(col) class(col)[1], ""), collapse = ",")
         """,
         """
         parsed = spec_tsv(I("x\\ty\\n1\\ta"))
         return ",".join("collector_" + collector.kind for collector in parsed.cols)
         """),
    case("stop_for_problems", "readr.read.stop_for_problems", "Stop when parsing failed",
         "Returns the data when there are no problems and raises when there is at least one.",
         "clean column, then a letter",
         """
         ok <- tryCatch({ stop_for_problems(read_csv(I("a\\n1"))); "ok" }, error = function(e) "err")
         bad <- tryCatch({ stop_for_problems(read_csv(I("a\\n1\\nb"), col_types = "d")); "ok" }, error = function(e) "err")
         paste(ok, bad)
         """,
         """
         try:
             stop_for_problems(read_csv(I("a\\n1"), show_col_types=False))
             ok = "ok"
         except ValueError:
             ok = "err"
         try:
             stop_for_problems(read_csv(I("a\\n1\\nb"), col_types="d", show_col_types=False))
             bad = "ok"
         except ValueError:
             bad = "err"
         return ok + " " + bad
         """, ["tibble"]),
    case("tokenize", "readr.read.tokenize", "Split records into fields",
         "A csv tokenizer skips a blank line. Each record is a character vector.",
         "1,2 then 3,4,5 then 6",
         """
         tokens <- tokenize(I("1,2\\n3,4,5\\n\\n6"))
         paste(vapply(tokens, function(row) paste(row, collapse = "|"), ""), collapse = ";")
         """,
         """
         tokens = tokenize(I("1,2\\n3,4,5\\n\\n6"))
         return ";".join("|".join(row) for row in tokens)
         """),
    case("tokenizer_csv", "readr.read.tokenizer_csv", "CSV tokenizer",
         "Comma delimiter, doubled quotes, and blank rows skipped.", "defaults",
         """
         token <- tokenizer_csv()
         paste(token$delim, token$quote, yn(token$skip_empty_rows), sep = ";")
         """,
         """
         token = tokenizer_csv()
         return token["delim"] + ";" + token["quote"] + ";" + yn(token["skip_empty_rows"])
         """),
    case("tokenizer_delim", "readr.read.tokenizer_delim", "Delimiter tokenizer",
         "The delimiter is the one you pass.", "pipe",
         """
         token <- tokenizer_delim("|")
         paste(token$delim, token$quote, yn(token$skip_empty_rows), sep = ";")
         """,
         """
         token = tokenizer_delim("|")
         return token["delim"] + ";" + token["quote"] + ";" + yn(token["skip_empty_rows"])
         """),
    case("tokenizer_fwf", "readr.read.tokenizer_fwf", "Fixed-width tokenizer",
         "Begin and end positions are stored on the tokenizer.", "0-4 and 5-10",
         """
         token <- tokenizer_fwf(c(0, 5), c(4, 10))
         paste(paste(token$begin, collapse = ","), paste(token$end, collapse = ","), sep = ";")
         """,
         """
         token = tokenizer_fwf([0, 5], [4, 10])
         return ",".join(str(value) for value in token["begin"]) + ";" + ",".join(str(value) for value in token["end"])
         """),
    case("tokenizer_line", "readr.read.tokenizer_line", "Line tokenizer",
         "Each line is one field. The default missing set is empty.", "defaults",
         """
         token <- tokenizer_line()
         paste(length(token$na), yn(token$skip_empty_rows), sep = ";")
         """,
         """
         token = tokenizer_line()
         return str(len(token["na"])) + ";" + yn(token["skip_empty_rows"])
         """),
    case("tokenizer_log", "readr.read.tokenizer_log", "Web-log tokenizer",
         "Splits a combined log line. Whitespace trimming follows the argument.", "trim",
         'yn(tokenizer_log(TRUE)$trim_ws)',
         'return yn(tokenizer_log(True)["trim_ws"])'),
    case("tokenizer_tsv", "readr.read.tokenizer_tsv", "TSV tokenizer",
         "The delimiter is a tab and blank rows are skipped.", "defaults",
         """
         token <- tokenizer_tsv()
         paste(if (identical(token$delim, "\\t")) "TAB" else token$delim, yn(token$skip_empty_rows), sep = ";")
         """,
         """
         token = tokenizer_tsv()
         delim = "TAB" if token["delim"] == "\\t" else token["delim"]
         return delim + ";" + yn(token["skip_empty_rows"])
         """),
    case("tokenizer_ws", "readr.read.tokenizer_ws", "Whitespace tokenizer",
         "Fields are split on runs of whitespace.", "defaults",
         """
         token <- tokenizer_ws()
         paste(token$na, yn(token$skip_empty_rows), sep = ";")
         """,
         """
         token = tokenizer_ws()
         return str(token["na"]) + ";" + yn(token["skip_empty_rows"])
         """),
    case("type_convert", "readr.read.type_convert", "Re-parse character columns",
         "Character columns are guessed again. Whole numbers become doubles.", "1, NA, and 2",
         """
         converted <- type_convert(data.frame(a = c("1", "NA", "2"), b = c("x", "y", "z"), stringsAsFactors = FALSE))
         paste(flatv(converted$a), flatv(converted$b), sep = ";")
         """,
         """
         converted = type_convert(frame(["a", "b"], [["1", "NA", "2"], ["x", "y", "z"]]))
         return flatv(converted.columns[0]) + ";" + flatv(converted.columns[1])
         """, ["tibble"]),
    case("with_edition", "readr.runtime.with_edition", "Run code under one edition",
         "Edition 1 pads a short row. Edition 2 glues extra fields into the last column. Python takes a callable.",
         "short first row under both editions",
         """
         first <- flatdf(with_edition(1, read_csv(I("1,2\\n3,4,5"), col_names = c("X", "Y", "Z"))))
         second <- flatdf(with_edition(2, read_csv(I("1,2\\n3,4,5"), col_names = c("X", "Y", "Z"))))
         paste(first, second, sep = " || ")
         """,
         """
         first = flatdf(with_edition(1, lambda: read_csv(I("1,2\\n3,4,5"), col_names=["X", "Y", "Z"], show_col_types=False)))
         second = flatdf(with_edition(2, lambda: read_csv(I("1,2\\n3,4,5"), col_names=["X", "Y", "Z"], show_col_types=False)))
         return first + " || " + second
         """, ["tibble", "withr"]),
    case("write_csv", "readr.write.write_csv", "Write CSV",
         "The file matches format_csv, including the trailing newline.", "one third and a comma",
         """
         path <- tempfile()
         write_csv(data.frame(a = c(1, 1/3, NA), b = c(TRUE, FALSE, NA), c = c("x", "a,b", NA)), path)
         readChar(path, file.info(path)$size)
         """,
         """
         path = tempfile.mktemp()
         write_csv(frame(["a", "b", "c"], [[1.0, 1/3, None], [True, False, None], ["x", "a,b", None]]), path)
         return Path(path).read_text()
         """, ["tibble"]),
    case("write_csv2", "readr.write.write_csv2", "Write European CSV",
         "Decimal commas and a semicolon separator.", "1.5",
         """
         path <- tempfile()
         write_csv2(data.frame(a = c(1.5, NA)), path)
         readChar(path, file.info(path)$size)
         """,
         """
         path = tempfile.mktemp()
         write_csv2(frame(["a"], [[1.5, None]]), path)
         return Path(path).read_text()
         """, ["tibble"]),
    case("write_delim", "readr.write.write_delim", "Write a delimiter",
         "The delimiter is the one you pass.", "pipe",
         """
         path <- tempfile()
         write_delim(data.frame(a = c(1, NA)), path, delim = "|")
         readChar(path, file.info(path)$size)
         """,
         """
         path = tempfile.mktemp()
         write_delim(frame(["a"], [[1.0, None]]), path, delim="|")
         return Path(path).read_text()
         """, ["tibble"]),
    case("write_excel_csv", "readr.write.write_excel_csv", "Write CSV with a BOM",
         "The file starts with the UTF-8 byte order mark so Excel reads it as UTF-8.", "one column",
         """
         path <- tempfile()
         write_excel_csv(data.frame(a = 1), path)
         raw <- readBin(path, "raw", file.info(path)$size)
         paste(paste(as.integer(raw[1:3]), collapse = ","), rawToChar(raw[4:length(raw)]), sep = "|")
         """,
         """
         path = tempfile.mktemp()
         write_excel_csv(frame(["a"], [[1.0]]), path)
         raw = Path(path).read_bytes()
         return ",".join(str(value) for value in raw[:3]) + "|" + raw[3:].decode()
         """, ["tibble"]),
    case("write_excel_csv2", "readr.write.write_excel_csv2", "Write European CSV with a BOM",
         "A byte order mark, semicolon separators, and comma decimals.", "1.5",
         """
         path <- tempfile()
         write_excel_csv2(data.frame(a = 1.5), path)
         raw <- readBin(path, "raw", file.info(path)$size)
         paste(paste(as.integer(raw[1:3]), collapse = ","), rawToChar(raw[4:length(raw)]), sep = "|")
         """,
         """
         path = tempfile.mktemp()
         write_excel_csv2(frame(["a"], [[1.5]]), path)
         raw = Path(path).read_bytes()
         return ",".join(str(value) for value in raw[:3]) + "|" + raw[3:].decode()
         """, ["tibble"]),
    case("write_file", "readr.write.write_file", "Write a string or bytes",
         "The bytes are written as given, with no extra newline.", "hello",
         """
         path <- tempfile()
         write_file("hello\\n", path)
         readChar(path, file.info(path)$size)
         """,
         """
         path = tempfile.mktemp()
         write_file("hello\\n", path)
         return Path(path).read_text()
         """),
    case("write_lines", "readr.write.write_lines", "Write one record per line",
         "Missing values become the na string. A separator follows the last line.", "a, NA, b",
         """
         path <- tempfile()
         write_lines(c("a", NA, "b"), path)
         readChar(path, file.info(path)$size)
         """,
         """
         path = tempfile.mktemp()
         write_lines(["a", None, "b"], path)
         return Path(path).read_text()
         """),
    case("write_tsv", "readr.write.write_tsv", "Write TSV",
         "Fields are separated by a tab.", "two columns",
         """
         path <- tempfile()
         write_tsv(data.frame(a = "a,b", b = 1), path)
         readChar(path, file.info(path)$size)
         """,
         """
         path = tempfile.mktemp()
         write_tsv(frame(["a", "b"], [["a,b"], [1.0]]), path)
         return Path(path).read_text()
         """, ["tibble"]),
    case("clipboard", "readr.clipboard", "Read the clipboard",
         "Edition 2 pastes the clipboard into one string.", "two lines",
         r"""
         Sys.setenv(CLIPR_ALLOW = "TRUE")
         x <- clipboard()
         gsub("\n", "|", paste(as.character(x), collapse = "|"), fixed = TRUE)
         """,
         """
         import os
         os.environ["CLIPR_ALLOW"] = "TRUE"
         return str(clipboard()).replace("\\n", "|")
         """, ["clipr"]),
    case("read_rds", "readr.rds.read_rds", "Read an RDS file",
         "Version 2 RDS, including gzip, bzip2, and xz wrappers.", "two rows and four wrappers",
         """
         base <- "/tmp/readr-from-r"
         df <- data.frame(a = c(1, NA), b = c(TRUE, NA), c = c("x", NA), stringsAsFactors = FALSE)
         saveRDS(df, paste0(base, ".rds"), version = 2, compress = FALSE)
         saveRDS(df, paste0(base, ".gz.rds"), version = 2, compress = "gzip")
         saveRDS(df, paste0(base, ".bz2.rds"), version = 2, compress = "bzip2")
         saveRDS(df, paste0(base, ".xz.rds"), version = 2, compress = "xz")
         parts <- c(
           flatdf(read_rds(paste0(base, ".rds"))),
           flatdf(read_rds(paste0(base, ".gz.rds"))),
           flatdf(read_rds(paste0(base, ".bz2.rds"))),
           flatdf(read_rds(paste0(base, ".xz.rds")))
         )
         paste(parts, collapse = " || ")
         """,
         """
         base = "/tmp/readr-from-r"
         parts = [flatdf(read_rds(base + suffix)) for suffix in (".rds", ".gz.rds", ".bz2.rds", ".xz.rds")]
         return " || ".join(parts)
         """, ["digest"]),
    case("write_rds", "readr.rds.write_rds", "Write an RDS file",
         "Version 2 with compress none matches saveRDS. gzip is compared after it is opened.", "two rows",
         """
         df <- data.frame(a = c(1, NA), b = c(TRUE, NA), c = c("x", NA), stringsAsFactors = FALSE)
         path <- "/tmp/readr-write.rds"
         gz <- "/tmp/readr-write.gz.rds"
         write_rds(df, path)
         write_rds(df, gz, compress = "gz")
         raw <- readBin(path, "raw", file.info(path)$size)
         packed <- memDecompress(readBin(gz, "raw", file.info(gz)$size), "gzip")
         paste0(paste(sprintf("%02x", as.integer(raw)), collapse = ""), " ",
                paste(sprintf("%02x", as.integer(packed)), collapse = ""))
         """,
         """
         import gzip
         df = frame(["a", "b", "c"], [[1.0, None], [True, None], ["x", None]])
         path = Path("/tmp/readr-write.rds")
         gz = Path("/tmp/readr-write.gz.rds")
         write_rds(df, path)
         write_rds(df, gz, compress="gz")
         return path.read_bytes().hex() + " " + gzip.decompress(gz.read_bytes()).hex()
         """, ["digest"]),
    case("read_builtin", "readr.read_builtin", "Read a built-in dataset",
         "Loads one named object from a package lazy-load database.", "mtcars",
         """
         x <- read_builtin("mtcars", "datasets")
         paste(nrow(x), sprintf("%.17g", x$mpg[1]), sprintf("%.17g", x$mpg[nrow(x)]), paste(names(x), collapse = ","), sep = "|")
         """,
         """
         x = read_builtin("mtcars", "datasets")
         return "|".join([str(x.nrow), format(x.columns[0][0], ".17g"), format(x.columns[0][-1], ".17g"), ",".join(x.names)])
         """, ["utils"]),
]


def _run_r(cases):
    parts = [R_HEADER]
    for item in cases:
        fname = "one_" + item["name"].replace(".", "_")
        parts.append(f"{fname} <- function() {{\n{item['r']}\n}}")
        parts.append(
            f"""
value <- tryCatch({fname}(), error = function(e) paste0("ERR:", conditionMessage(e)))
if (is.null(value)) value <- "NULL"
if (!is.character(value)) value <- as.character(value)
if (length(value) != 1) value <- paste(value, collapse = ",")
elapsed <- numeric(20)
for (i in seq_len(20)) {{
  t0 <- as.numeric(Sys.time())
  tryCatch({fname}(), error = function(e) NULL)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}}
cat("{item['name']}\\n", nchar(value), "\\n", sep = "")
cat(value, sep = "")
cat("\\n", sprintf("%.17g", median(elapsed) * 1000), "\\n", sep = "")
"""
        )
    path = Path("/tmp/readr-batch.R")
    path.write_text("\n".join(parts))
    completed = subprocess.run(["Rscript", str(path)], check=True, capture_output=True, text=True)
    return _parse_blocks(completed.stdout)


def _parse_blocks(text):
    found = {}
    while text:
        name, text = text.split("\n", 1)
        count, text = text.split("\n", 1)
        count = int(count)
        value = text[:count]
        text = text[count:]
        if not text.startswith("\n"):
            raise RuntimeError(f"bad block after {name}")
        text = text[1:]
        ms, text = text.split("\n", 1)
        found[name] = (value, float(ms))
    return found


def _run_py(item, namespace):
    source = "def one():\n" + textwrap.indent(item["py"], "    ")
    local = dict(namespace)
    exec(source, local)
    one = local["one"]
    try:
        value = one()
    except Exception as exc:
        value = f"ERR:{exc}"
    if value is None:
        value = "NULL"
    value = str(value)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        try:
            one()
        except Exception:
            pass
        elapsed.append((time.perf_counter() - started) * 1000)
    return value, statistics.median(elapsed)


def _doc(item, value):
    arguments = [
        {"name": "x", "text": "The data, path, or collector this function accepts."},
    ]
    side = {
        "description": item["desc"],
        "usage": f"{item['name']}()",
        "arguments": arguments,
        "details": item["desc"],
        "value": "The same value readr 2.2.0 returns for this case, written as one line in the output.",
        "example": item["r"],
    }
    origin = dict(side)
    origin["output"] = f"output/{item['name']}-r.txt"
    translated = dict(side)
    translated["example"] = item["py"]
    translated["output"] = f"output/{item['name']}-python.txt"
    return {"name": item["name"], "title": item["title"], "origin": origin, "translation": translated}


def _record(item, r_ms, py_ms, matched):
    speedup = (r_ms / py_ms) if py_ms else None
    proof_r = R_HEADER + "\none <- function() {\n" + item["r"] + "\n}\n" + LOOP_R
    proof_py = PY_HEADER + "\ndef one():\n" + textwrap.indent(item["py"], "    ") + "\n" + LOOP_PY
    if item["name"] == "clipboard":
        proof_r = "Sys.setenv(CLIPR_ALLOW = \"TRUE\")\nsystem(\"printf 'a\\\\nb' | xclip -selection clipboard\")\n" + proof_r
        proof_py = "import os\nimport subprocess\nos.environ['CLIPR_ALLOW'] = 'TRUE'\nos.environ.setdefault('DISPLAY', ':0')\nsubprocess.run(['xclip', '-selection', 'clipboard'], input=b'a\\nb', check=True)\n" + proof_py
    return {
        "name": item["name"],
        "translated": matched,
        "python": item["python"],
        "loads": item["loads"],
        "uses": [],
        "done": item["desc"] if matched else "",
        "not_done": "" if matched else "The check against readr 2.2.0 did not match.",
        "blocked_by": [],
        "assigned": "",
        "check": {
            "case": item["label"],
            "r_ms": r_ms,
            "translated_ms": py_ms,
            "speedup": speedup,
            "matches": matched,
            "max_abs_diff": 0.0 if matched else None,
            "tolerance": 1e-8,
            "proof": {"r": proof_r, "python": proof_py},
        },
    }


def _unfinished(name):
    return {
        "name": name,
        "translated": False,
        "python": "",
        "loads": [],
        "uses": [],
        "done": "",
        "not_done": UNFINISHED[name],
        "blocked_by": [],
        "assigned": "",
    }


def main():
    import sys

    for extra in ("readr", "tibble", "withr", "stringi", "clipr", "digest", "utils"):
        path = str(REPO / "packages" / extra)
        if path not in sys.path:
            sys.path.insert(0, path)
    by_name = {item["name"]: item for item in CASES}
    missing = [name for name in ORDER if name not in by_name and name not in UNFINISHED]
    if missing:
        raise SystemExit("missing cases: " + ", ".join(missing))
    namespace = {}
    exec(PY_HEADER, namespace)
    os.environ["CLIPR_ALLOW"] = "TRUE"
    os.environ.setdefault("DISPLAY", ":0")
    subprocess.run(["xclip", "-selection", "clipboard"], input=b"a\nb", check=True)
    origin = _run_r(CASES)
    mismatches = []
    written = []
    functions = []
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    for name in ORDER:
        if name in UNFINISHED:
            functions.append(_unfinished(name))
            continue
        item = by_name[name]
        r_value, r_ms = origin[name]
        py_value, py_ms = _run_py(item, namespace)
        matched = r_value == py_value and not r_value.startswith("ERR:")
        if not matched:
            mismatches.append((name, py_value, r_value))
        record = _record(item, r_ms, py_ms, matched)
        if matched:
            (OUTPUT / f"{name}-r.txt").write_text(r_value + "\n")
            (OUTPUT / f"{name}-python.txt").write_text(py_value + "\n")
            (DOCS / f"{name}.json").write_text(json.dumps(_doc(item, r_value), indent=2) + "\n")
            (PROOF / f"{name}-r.R").write_text(record["check"]["proof"]["r"])
            (PROOF / f"{name}-py.py").write_text(record["check"]["proof"]["python"])
        functions.append(record)
        written.append(name if matched else name + " DIFFERS")
    done = sum(1 for item in functions if item["translated"])
    translation = {
        "name": "readr",
        "cran_version": "2.2.0",
        "inventory": "complete",
        "status": "complete" if done == len(functions) else "in_progress",
        "blocked_by": [],
        "crate_claims": [],
        "resume": "Edition 2 reads and writes delimited text in Python. Types are guessed the way vroom guesses them, so whole numbers are doubles. Time zones use zoneinfo. read_rds and write_rds use digest's version-2 serializer. read_builtin loads a named dataset from a package lazy-load database. Compression code 3 is raw LZMA2 with a 5-byte header.",
        "dependencies": {
            "translated": ["clipr", "digest", "stringi", "tibble", "utils", "withr"],
            "native": ["bz2", "gzip", "lzma", "zoneinfo"],
            "rust": [],
        },
        "functions": functions,
    }
    (ROOT / "translation.json").write_text(json.dumps(translation, indent=2) + "\n")
    print(f"matched {done} of {len(functions)}")
    for name, py_value, r_value in mismatches:
        print("---", name)
        print(" py", repr(py_value)[:500])
        print(" r ", repr(r_value)[:500])


if __name__ == "__main__":
    main()
