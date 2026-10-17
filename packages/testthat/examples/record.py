"""Check every testthat export against R, capture examples, and write the records.

The orchestrator runs this once. Sub-agents do not edit translation.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "output"
PROOF = ROOT / "proof"
PY = REPO / ".venv" / "bin" / "python"

R_HELPER = r"""
caught <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e), skip = function(e) conditionMessage(e))
}
json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  paste0("\"", x, "\"")
}
to_json <- function(x) {
  if (is.null(x)) return("null")
  if (is.logical(x)) {
    bits <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    if (length(bits) == 1) return(bits)
    return(paste0("[", paste(bits, collapse = ","), "]"))
  }
  if (is.character(x)) {
    if (length(x) == 1) return(json_escape(x))
    return(paste0("[", paste(vapply(x, json_escape, ""), collapse = ","), "]"))
  }
  if (is.numeric(x)) {
    if (length(x) == 1) return(sprintf("%.17g", x))
    return(paste0("[", paste(sprintf("%.17g", x), collapse = ","), "]"))
  }
  stop(paste("unsupported", paste(class(x), collapse = ",")))
}
"""

R_SHOW = r"""
show <- function(x) {
  if (is.null(x)) { cat("NULL\n"); return() }
  if (is.logical(x) && length(x) == 1) { cat(if (isTRUE(x)) "TRUE\n" else "FALSE\n"); return() }
  if (is.numeric(x) && length(x) && all(abs(x - round(x)) < 1e-8)) {
    cat(sprintf("%.0f", x), sep = " ")
  } else if (is.numeric(x)) {
    cat(sprintf("%.8f", x), sep = " ")
  } else {
    cat(paste(x, collapse = " "))
  }
  cat("\n")
}
"""

PY_SHOW = '''
def show(x):
    if x is None:
        print("NULL")
        return
    if isinstance(x, bool):
        print("TRUE" if x else "FALSE")
        return
    if isinstance(x, (int, float)):
        x = [x]
    if isinstance(x, list) and x and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x):
        if all(abs(v - round(v)) < 1e-8 for v in x):
            print(" ".join(str(int(round(v))) for v in x))
        else:
            print(" ".join(f"{v:.8f}" for v in x))
        return
    if isinstance(x, list):
        print(" ".join(str(v) for v in x))
        return
    print(x)
'''

PY_NAMES = {
    "%>%": "pipe",
    "is.expectation": "is_expectation",
    "not": "not_",
    "pass": "pass_",
}

DESC_MISSING = """Could not find a root 'DESCRIPTION' file that starts with '^Package' in
'/tmp/no-such-tt-dir'.
ℹ Are you in your project directory and does your project have a 'DESCRIPTION'
  file?"""

TEARDOWN_ENV = """`teardown_env()` has not been initialized.
ℹ This is an internal error that was detected in the testthat package.
  Please report it at <https://github.com/r-lib/testthat/issues> with a reprex
  (<https://tidyverse.org/help/>) and the full backtrace."""


def cases() -> list[dict]:
    out: list[dict] = []

    def add(name, title, description, story, r, py, uses=None, loads=None, arguments=None):
        out.append(dict(
            name=name,
            title=title,
            description=description,
            story=story,
            r=r.strip(),
            py=py.strip(),
            uses=uses or [],
            loads=loads or [],
            arguments=arguments or [],
        ))

    add("%>%", "Pipe", "Pass a value into the next function.", "2 piped into plus 3",
        "2 %>% `+`(3)",
        "value = pipe(2, lambda x: x + 3)\nreturn value.force() if hasattr(value, 'force') else value",
        loads=["magrittr"])

    for name in [
        "CheckReporter", "CompactProgressReporter", "DebugReporter", "FailReporter",
        "JunitReporter", "ListReporter", "LlmReporter", "LocationReporter",
        "MinimalReporter", "ParallelProgressReporter", "ProgressReporter",
        "RStudioReporter", "Reporter", "SilentReporter", "SlowReporter",
        "StopReporter", "SummaryReporter", "TapReporter", "TeamcityReporter",
    ]:
        add(name, name, f"Construct a {name}.", f"class of {name}",
            f'class({name}$new())[1]',
            f'return type({name}()).__name__')

    add("MultiReporter", "MultiReporter", "Construct a reporter that forwards to others.",
        "class of MultiReporter",
        'class(MultiReporter$new(reporters = list(SilentReporter$new())))[1]',
        'return type(MultiReporter([SilentReporter()])).__name__')

    add("announce_snapshot_file", "Announce a snapshot file",
        "In edition 3, record a file snapshot and return nothing.",
        "announce a one-line file",
        """
local({
  local_edition(3)
  f <- tempfile(); writeLines("hi", f)
  announce_snapshot_file(f, "demo")
})
""",
        """
with local_edition(3):
    fd, f = tempfile.mkstemp()
    os.close(fd)
    open(f, "w").write("hi\\n")
    return announce_snapshot_file(f, "demo")
""")

    add("auto_test", "Watch and re-run tests", "Report that the paths hold no tests.",
        "auto_test on missing paths",
        'caught(auto_test("nope", "nope"))',
        'return caught(lambda: auto_test("nope", "nope"))')

    add("auto_test_package", "Watch a package", "Look for a DESCRIPTION in the working directory.",
        "auto_test_package() in /tmp",
        "caught(auto_test_package())",
        "return caught(lambda: auto_test_package())")

    add("capture_condition", "Capture a condition", "Return the message of a raised error.",
        'capture_condition(stop("boom"))',
        'conditionMessage(capture_condition(stop("boom")))',
        'return str(capture_condition(lambda: (_ for _ in ()).throw(RuntimeError("boom"))))')

    add("capture_error", "Capture an error", "Return the message of a raised error.",
        'capture_error(stop("boom"))',
        'conditionMessage(capture_error(stop("boom")))',
        'return str(capture_error(lambda: (_ for _ in ()).throw(RuntimeError("boom"))))')

    add("capture_expectation", "Capture an expectation", "A forced failure is an expectation.",
        "capture_expectation(fail(\"forced\"))",
        'is.expectation(capture_expectation(fail("forced")))',
        'return is_expectation(capture_expectation(lambda: fail("forced")))')

    add("capture_message", "Capture one message", "message() text, including the newline.",
        'capture_message(message("hello"))',
        'conditionMessage(capture_message(message("hello")))',
        'return capture_message(lambda: message("hello"))')

    add("capture_messages", "Capture messages", "message() text, including the newline.",
        'capture_messages(message("hello"))',
        'capture_messages(message("hello"))',
        'return capture_messages(lambda: message("hello"))[0]')

    add("capture_output", "Capture stdout", "Text written to stdout.",
        'capture_output(cat("hi"))',
        'capture_output(cat("hi"))',
        'return capture_output(lambda: print("hi", end=""))')

    add("capture_output_lines", "Capture stdout lines", "One printed line, without the newline.",
        'capture_output_lines(cat("hi\\n"))',
        'capture_output_lines(cat("hi\\n"))',
        'return capture_output_lines(lambda: print("hi"))[0]')

    add("capture_warning", "Capture a warning", "The warning message.",
        'capture_warning(warning("careful"))',
        'capture_warning(warning("careful"))$message',
        'return str(capture_warning(lambda: warnings.warn("careful")).message)')

    add("capture_warnings", "Capture warnings", "The warning message.",
        'capture_warnings(warning("careful"))',
        'capture_warnings(warning("careful"))',
        'return capture_warnings(lambda: warnings.warn("careful"))[0]')

    add("check_reporter", "Check reporter name", "The reporter used by test_check().",
        "check_reporter()", "check_reporter()", "return check_reporter()")

    add("compare", "Compare two values", "Edition 2 compare of equal numbers.",
        "compare(1, 1)", "compare(1, 1)$equal", "return compare(1, 1).equal")

    add("compare_file_binary", "Compare files as bytes", "Two files with the same bytes.",
        "identical binary files",
        """
a <- tempfile(); b <- tempfile()
writeBin(as.raw(c(1, 2, 3)), a)
writeBin(as.raw(c(1, 2, 3)), b)
compare_file_binary(a, b)
""",
        """
a = tempfile.mktemp(); b = tempfile.mktemp()
open(a, "wb").write(bytes([1, 2, 3]))
open(b, "wb").write(bytes([1, 2, 3]))
return compare_file_binary(a, b)
""")

    add("compare_file_text", "Compare files as text", "Two files with the same lines.",
        "identical text files",
        """
a <- tempfile(); b <- tempfile()
writeLines("hi", a); writeLines("hi", b)
compare_file_text(a, b)
""",
        """
a = tempfile.mktemp(); b = tempfile.mktemp()
open(a, "w").write("hi\\n"); open(b, "w").write("hi\\n")
return compare_file_text(a, b)
""")

    add("context", "Test context", "context() records a label and returns nothing.",
        'context("String processing")', 'context("String processing")', 'return context("String processing")')

    add("context_start_file", "Context from a file name", "Start a context from a test file name.",
        "context_start_file of test-foo.R",
        'context_start_file("test-foo.R")',
        'return context_start_file("test-foo.R")')

    add("default_compact_reporter", "Compact reporter name", "The compact reporter, or Llm under a coding agent.",
        "default_compact_reporter()", "default_compact_reporter()", "return default_compact_reporter()")

    add("default_reporter", "Default reporter name", "The default reporter, or Llm under a coding agent.",
        "default_reporter()", "default_reporter()", "return default_reporter()")

    add("describe", "describe()", "A describe block is a test.",
        "describe a passing expectation",
        'describe("ok", { expect_true(TRUE); TRUE })',
        'return describe("ok", lambda: expect_true(True))')

    add("edition_get", "Testthat edition", "Outside a package DESCRIPTION the edition is 2.",
        "edition_get()", "edition_get()", "return edition_get()")

    add("equals", "equals()", "Old-style equality predicate.",
        "equals(2)(2)", "equals(2)(2)", "return equals(2)(2)")

    add("equals_reference", "equals_reference()", "Old-style predicate factory.",
        "equals_reference is a function",
        'is.function(equals_reference("nope"))',
        'return callable(equals_reference("nope"))')

    add("evaluate_promise", "Evaluate a promise", "The value of the expression.",
        "evaluate_promise(1)", "evaluate_promise(1)$result",
        'return evaluate_promise(lambda: 1)["result"]')

    add("expect", "expect()", "A TRUE condition is an expectation.",
        "expect(TRUE, \"ok\")",
        'is.expectation(expect(TRUE, "ok"))',
        'return is_expectation(expect(True, "ok"))')

    add("expect_all_equal", "All elements equal", "Every element equals the expected value.",
        "expect_all_equal(c(1, 1), 1)", "expect_all_equal(c(1, 1), 1)",
        "return expect_all_equal([1, 1], 1)")

    add("expect_all_false", "All elements FALSE", "Every element is FALSE.",
        "expect_all_false(c(FALSE, FALSE))", "expect_all_false(c(FALSE, FALSE))",
        "return expect_all_false([False, False])")

    add("expect_all_true", "All elements TRUE", "Every element is TRUE.",
        "expect_all_true(c(TRUE, TRUE))", "expect_all_true(c(TRUE, TRUE))",
        "return expect_all_true([True, True])")

    add("expect_condition", "Expect a condition", "stop() raises a condition.",
        'expect_condition(stop("boom"))',
        'conditionMessage(expect_condition(stop("boom"), regexp = "boom"))',
        'return str(expect_condition(lambda: (_ for _ in ()).throw(RuntimeError("boom")), "boom"))')

    add("expect_contains", "Expect a subset", "The object contains the expected values.",
        'expect_contains(c("a", "b"), "a")',
        'expect_contains(c("a", "b", "c"), c("a", "c"))',
        'return expect_contains(["a", "b", "c"], ["a", "c"])')

    add("expect_cpp_tests_pass", "C++ tests", "A missing package is reported with the R wording.",
        "expect_cpp_tests_pass(\"not_a_pkg\")",
        'caught(expect_cpp_tests_pass("not_a_pkg"))',
        'return caught(lambda: expect_cpp_tests_pass("not_a_pkg"))')

    add("expect_disjoint", "Disjoint values", "The two vectors share no values.",
        'expect_disjoint("a", "b")',
        'expect_disjoint("a", "b")',
        'return expect_disjoint("a", "b")')

    add("expect_equal", "Equal values", "Edition 2 reports a numeric mismatch.",
        "expect_equal(1, 2) failure",
        "caught(expect_equal(1, 2))",
        "return caught(lambda: expect_equal(1, 2))")

    add("expect_equal_to_reference", "Equal to a reference file", "A missing reference file is created from the value.",
        "expect_equal_to_reference(1, tempfile)",
        """
p <- tempfile()
expect_equal_to_reference(1, p)
""",
        """
p = tempfile.mktemp()
return expect_equal_to_reference(1, p)
""")

    add("expect_equivalent", "Equivalent values", "Edition 2 equivalence of two numbers.",
        "expect_equivalent(1, 1)", "expect_equivalent(1, 1)", "return expect_equivalent(1, 1)")

    add("expect_error", "Expect an error", "The error message matches the pattern.",
        'expect_error(stop("boom"), "boom")',
        'conditionMessage(expect_error(stop("boom"), "boom"))',
        'return str(expect_error(lambda: (_ for _ in ()).throw(RuntimeError("boom")), "boom"))')

    add("expect_failure", "Expect a failure", "A failing expectation is a failure.",
        "expect_failure(expect_true(FALSE))",
        "expect_failure(expect_true(FALSE))",
        "return expect_failure(lambda: expect_true(False))")

    add("expect_false", "Expect FALSE", "FALSE is FALSE.",
        "expect_false(FALSE)", "expect_false(FALSE)", "return expect_false(False)")

    add("expect_gt", "Greater than", "3 is greater than 1.",
        "expect_gt(3, 1)", "expect_gt(3, 1)", "return expect_gt(3, 1)")

    add("expect_gte", "Greater than or equal", "1 is greater than or equal to 1.",
        "expect_gte(1, 1)", "expect_gte(1, 1)", "return expect_gte(1, 1)")

    add("expect_identical", "Identical values", "Two doubles are identical.",
        "expect_identical(1, 1)", "expect_identical(1, 1)", "return expect_identical(1.0, 1.0)")

    add("expect_in", "Values drawn from a set", "a is in a and b.",
        'expect_in("a", c("a", "b"))',
        'expect_in("a", c("a", "b"))',
        'return expect_in("a", ["a", "b"])')

    add("expect_invisible", "Invisible result", "An invisible value passes.",
        "expect_invisible(invisible(1))",
        "expect_invisible(invisible(1))",
        """
def f():
    return 1
f.invisible = True
return expect_invisible(f)
""")

    add("expect_is", "inherits()", "A number inherits from numeric.",
        'expect_is(1, "numeric")', 'expect_is(1, "numeric")', 'return expect_is(1, "numeric")')

    add("expect_known_hash", "Known hash", "The digest of 1 matches digest::digest.",
        "expect_known_hash(1, digest(1))",
        """
h <- digest::digest(1)
expect_known_hash(1, h)
""",
        """
from digest import digest, real
h = digest(real([1.0]))
return expect_known_hash(1.0, h)
""",
        loads=["digest"])

    add("expect_known_output", "Known output", "Captured output matches a file.",
        "expect_known_output of hi",
        """
p <- tempfile()
cat("hi\\n", file = p)
expect_known_output(cat("hi\\n"), p)
"ok"
""",
        """
p = tempfile.mktemp()
open(p, "w").write("hi\\n")
expect_known_output(lambda: print("hi"), p)
return "ok"
""")

    add("expect_known_value", "Known value", "A missing reference file is written from the value.",
        "expect_known_value(1, tempfile)",
        """
p <- tempfile()
expect_known_value(1, p)
""",
        """
p = tempfile.mktemp()
return expect_known_value(1, p)
""")

    add("expect_length", "Length", "A length-one value has length 1.",
        "expect_length(1, 1)", "expect_length(1, 1)", "return expect_length(1, 1)")

    add("expect_less_than", "expect_less_than", "Deprecated spelling of expect_lt.",
        "expect_less_than(9, 10)", "expect_less_than(9, 10)", "return expect_less_than(9, 10)")

    add("expect_lt", "Less than", "9 is less than 10.",
        "expect_lt(9, 10)", "expect_lt(9, 10)", "return expect_lt(9, 10)")

    add("expect_lte", "Less than or equal", "1 is less than or equal to 1.",
        "expect_lte(1, 1)", "expect_lte(1, 1)", "return expect_lte(1, 1)")

    add("expect_mapequal", "Named lists equal", "The shared name holds 1.",
        "expect_mapequal(list(a=1), list(a=1))",
        "expect_mapequal(list(a = 1), list(a = 1))$a",
        'return expect_mapequal({"a": 1}, {"a": 1})["a"]')

    add("expect_match", "Regular expression", "The string contains fun.",
        'expect_match("Testing is fun", "fun")',
        'expect_match("Testing is fun", "fun")',
        'return expect_match("Testing is fun", "fun")')

    add("expect_message", "Expect a message", "message() returns nothing.",
        'expect_message(message("hello"), "hello")',
        'expect_message(message("hello"), "hello")',
        'return expect_message(lambda: message("hello"), "hello")')

    add("expect_more_than", "expect_more_than", "Deprecated spelling of expect_gt.",
        "expect_more_than(3, 1)", "expect_more_than(3, 1)", "return expect_more_than(3, 1)")

    add("expect_named", "Names", "The values under the expected names.",
        'expect_named(c(a=1, b=2), c("a", "b"))',
        'unname(expect_named(c(a = 1, b = 2), c("a", "b")))',
        'return list(expect_named({"a": 1, "b": 2}, ["a", "b"]).values())')

    add("expect_no_condition", "No condition", "A plain value raises nothing.",
        "expect_no_condition(1)", "expect_no_condition(1)", "return expect_no_condition(1)")

    add("expect_no_error", "No error", "A plain value does not error.",
        "expect_no_error(1)", "expect_no_error(1)", "return expect_no_error(1)")

    add("expect_no_failure", "No failure", "Deprecated spelling of expect_success.",
        "expect_no_failure(expect_true(TRUE))",
        "expect_no_failure(expect_true(TRUE))",
        "return expect_no_failure(lambda: expect_true(True))")

    add("expect_no_match", "Does not match", "abc does not match z.",
        'expect_no_match("abc", "z")',
        'expect_no_match("abc", "z")',
        'return expect_no_match("abc", "z")')

    add("expect_no_message", "No message", "A plain value sends no message.",
        "expect_no_message(1)", "expect_no_message(1)", "return expect_no_message(1)")

    add("expect_no_success", "No success", "Deprecated spelling of expect_failure.",
        "expect_no_success(expect_true(FALSE))",
        "expect_no_success(expect_true(FALSE))",
        "return expect_no_success(lambda: expect_true(False))")

    add("expect_no_warning", "No warning", "A plain value warns nothing.",
        "expect_no_warning(1)", "expect_no_warning(1)", "return expect_no_warning(1)")

    add("expect_null", "Expect NULL", "NULL is NULL.",
        "expect_null(NULL)", "expect_null(NULL)", "return expect_null(None)")

    add("expect_output", "Expect output", "Printed text matches, and the value is returned.",
        'expect_output({cat("hi"); 1}, "hi")',
        'expect_output({ cat("hi"); 1 }, "hi")',
        """
def f():
    print("hi", end="")
    return 1
return expect_output(f, "hi")
""")

    add("expect_output_file", "Output file", "Captured output matches a file.",
        "expect_output_file of hi",
        """
p <- tempfile()
cat("hi\\n", file = p)
expect_output_file(cat("hi\\n"), p)
"ok"
""",
        """
p = tempfile.mktemp()
open(p, "w").write("hi\\n")
expect_output_file(lambda: print("hi"), p)
return "ok"
""")

    add("expect_r6_class", "R6 class", "An R6 object inherits from its class name.",
        "expect_r6_class of Foo",
        """
Foo <- R6::R6Class("Foo")
class(expect_r6_class(Foo$new(), "Foo"))[1]
""",
        """
class Foo:
    pass
return type(expect_r6_class(Foo(), "Foo")).__name__
""")

    add("expect_reference", "Same reference", "An object is a reference to itself.",
        "expect_reference(x, x)",
        """
x <- 1:3
expect_reference(x, x)
""",
        """
x = [1, 2, 3]
return expect_reference(x, x)
""")

    add("expect_s3_class", "S3 class", "An object with class box.",
        'expect_s3_class(structure(1, class = "box"), "box")',
        """
x <- structure(1, class = "box")
class(expect_s3_class(x, "box"))[1]
""",
        """
class Box:
    classes = ["box"]
return expect_s3_class(Box(), "box").classes[0]
""")

    add("expect_s4_class", "S4 class", "An S4 object of the declared class.",
        "expect_s4_class of ttbox",
        """
setClass("ttbox", slots = c(a = "numeric"))
class(expect_s4_class(new("ttbox"), "ttbox"))[1]
""",
        """
class ttbox:
    s4 = True
    classes = ["ttbox"]
return expect_s4_class(ttbox(), "ttbox").classes[0]
""")

    add("expect_s7_class", "S7 class", "S7 is not installed, so the check stops.",
        'expect_s7_class(1, "nope")',
        'caught(expect_s7_class(1, "nope"))',
        'return caught(lambda: expect_s7_class(1, "nope"))')

    add("expect_setequal", "Same set", "Order does not matter.",
        'expect_setequal(c("a", "b"), c("b", "a"))',
        'expect_setequal(c("a", "b"), c("b", "a"))',
        'return expect_setequal(["a", "b"], ["b", "a"])')

    add("expect_shape", "Matrix shape", "A 2 by 2 matrix has 2 rows.",
        "expect_shape(matrix, nrow = 2)",
        """
x <- matrix(1:4, nrow = 2)
paste(dim(expect_shape(x, nrow = 2)), collapse = "x")
""",
        """
import numpy as np
x = np.arange(1, 5).reshape(2, 2)
return "x".join(str(int(v)) for v in expect_shape(x, nrow=2).shape)
""",
        uses=["numpy"])

    add("expect_silent", "Silent code", "A plain value makes no noise.",
        "expect_silent(1)", "expect_silent(1)", "return expect_silent(1)")

    for name, call_r, call_py in [
        ("expect_snapshot", "expect_snapshot(1)", "return expect_snapshot(1)"),
        ("expect_snapshot_error", 'expect_snapshot_error(stop("boom"))',
         'return expect_snapshot_error(lambda: (_ for _ in ()).throw(RuntimeError("boom")))'),
        ("expect_snapshot_failure", "expect_snapshot_failure(expect_true(FALSE))",
         "return expect_snapshot_failure(lambda: expect_true(False))"),
        ("expect_snapshot_output", 'expect_snapshot_output(cat("hi"))',
         'return expect_snapshot_output(lambda: print("hi", end=""))'),
        ("expect_snapshot_value", "expect_snapshot_value(1)", "return expect_snapshot_value(1)"),
        ("expect_snapshot_warning", 'expect_snapshot_warning(warning("careful"))',
         'return expect_snapshot_warning(lambda: warnings.warn("careful"))'),
    ]:
        add(name, name, "Edition 3 snapshot. The call returns nothing.",
            f"{name}() under edition 3",
            f"local({{\n  local_edition(3)\n  {call_r}\n}})",
            f"with local_edition(3):\n    {call_py}")

    add("expect_snapshot_file", "Snapshot a file", "Edition 3 file snapshot returns nothing.",
        "expect_snapshot_file under edition 3",
        """
local({
  local_edition(3)
  f <- tempfile(); writeLines("hi", f)
  expect_snapshot_file(f, "demo")
})
""",
        """
with local_edition(3):
    fd, f = tempfile.mkstemp()
    os.close(fd)
    open(f, "w").write("hi\\n")
    return expect_snapshot_file(f, "demo")
""")

    add("expect_success", "Expect a success", "A passing expectation is a success.",
        "expect_success(expect_true(TRUE))",
        "expect_success(expect_true(TRUE))",
        "return expect_success(lambda: expect_true(True))")

    add("expect_that", "expect_that", "Old-style expect_that with equals.",
        "expect_that(10, equals(10))", "expect_that(5 * 2, equals(10))",
        "return expect_that(10, equals(10))")

    add("expect_true", "Expect TRUE", "TRUE is TRUE.",
        "expect_true(TRUE)", "expect_true(TRUE)", "return expect_true(True)")

    add("expect_type", "Storage type", "An integer has type integer.",
        'expect_type(1L, "integer")', 'expect_type(1L, "integer")',
        'return expect_type(1, "integer")')

    add("expect_vector", "Vector size", "A length-three integer vector.",
        "expect_vector(1:3, integer(), 3)", "expect_vector(1:3, integer(), 3)",
        "return expect_vector([1, 2, 3], size=3)")

    add("expect_visible", "Visible result", "A plain value is visible.",
        "expect_visible(1)", "expect_visible(1)", "return expect_visible(1)")

    add("expect_warning", "Expect a warning", "The code warns and returns 4.",
        'expect_warning({warning("careful"); 4}, "careful")',
        'expect_warning({ warning("careful"); 4 }, "careful")',
        """
def f():
    warnings.warn("careful")
    return 4
return expect_warning(f, "careful")
""")

    add("expectation", "Build an expectation", "A success expectation is an expectation.",
        'expectation("success", "ok")',
        'is.expectation(expectation("success", "ok"))',
        'return is_expectation(expectation("success", "ok"))')

    add("exp_signal", "Signal an expectation", "Signalling a success returns an expectation.",
        'exp_signal(new_expectation("success", "ok"))',
        'is.expectation(exp_signal(new_expectation("success", "ok")))',
        'return is_expectation(exp_signal(new_expectation("success", "ok")))')

    add("extract_test", "Extract a reprex", "A location without a line number is rejected.",
        'extract_test("nope.R")',
        'caught(extract_test("nope.R"))',
        'return caught(lambda: extract_test("nope.R"))')

    add("fail", "Force a failure", "fail() raises the given message.",
        'fail("forced")', 'caught(fail("forced"))', 'return caught(lambda: fail("forced"))')

    add("find_test_scripts", "Find test files", "An empty directory has no test scripts.",
        "length(find_test_scripts(empty))",
        """
d <- tempfile(); dir.create(d)
length(find_test_scripts(d))
""",
        """
d = tempfile.mkdtemp()
return len(find_test_scripts(d))
""")

    add("get_reporter", "Active reporter", "No reporter is active at the start.",
        "get_reporter()", "get_reporter()", "return get_reporter()")

    add("gives_warning", "gives_warning()", "Old-style warning predicate.",
        'gives_warning("careful")',
        'gives_warning("careful")({ warning("careful"); 4 })',
        """
def f():
    warnings.warn("careful")
    return 4
return gives_warning("careful")(f)
""")

    add("has_names", "has_names()", "Old-style names predicate.",
        'has_names(c("a", "b"))',
        'unname(has_names(c("a", "b"))(c(a = 1, b = 2)))',
        'return list(has_names(["a", "b"])({"a": 1, "b": 2}).values())')

    add("is.expectation", "Is an expectation", "A signalled success is an expectation.",
        'is.expectation(expect(TRUE, "ok"))',
        'is.expectation(expect(TRUE, "ok"))',
        'return is_expectation(expect(True, "ok"))')

    add("is_a", "is_a()", "Old-style inheritance predicate.",
        'is_a("numeric")(1)', 'is_a("numeric")(1)', 'return is_a("numeric")(1)')

    add("is_checking", "Inside R CMD check", "TRUE when TESTTHAT_IS_CHECKING is true.",
        "is_checking()",
        """
Sys.setenv(TESTTHAT_IS_CHECKING = "true")
is_checking()
""",
        """
os.environ["TESTTHAT_IS_CHECKING"] = "true"
return is_checking()
""")

    add("is_equivalent_to", "is_equivalent_to()", "Old-style equivalence predicate.",
        "is_equivalent_to(1)(1)", "is_equivalent_to(1)(1)", "return is_equivalent_to(1)(1)")

    add("is_identical_to", "is_identical_to()", "Old-style identity predicate.",
        "is_identical_to(1)(1)", "is_identical_to(1L)(1L)", "return is_identical_to(1)(1)")

    add("is_informative_error", "Defunct predicate", "Removed in testthat 3.0.0.",
        "is_informative_error(1)",
        "caught(is_informative_error(1))",
        "return caught(lambda: is_informative_error(1))")

    add("is_less_than", "is_less_than()", "Old-style less-than predicate.",
        "is_less_than(3)(1)", "is_less_than(3)(1)", "return is_less_than(3)(1)")

    add("is_more_than", "is_more_than()", "Old-style greater-than predicate.",
        "is_more_than(1)(3)", "is_more_than(1)(3)", "return is_more_than(1)(3)")

    add("is_parallel", "Parallel tests", "TRUE when TESTTHAT_IS_PARALLEL is true.",
        "is_parallel()",
        """
Sys.setenv(TESTTHAT_IS_PARALLEL = "true")
is_parallel()
""",
        """
os.environ["TESTTHAT_IS_PARALLEL"] = "true"
return is_parallel()
""")

    add("is_snapshot", "Inside a snapshot", "TRUE when TESTTHAT_IS_SNAPSHOT is true.",
        "is_snapshot()",
        """
Sys.setenv(TESTTHAT_IS_SNAPSHOT = "true")
is_snapshot()
""",
        """
os.environ["TESTTHAT_IS_SNAPSHOT"] = "true"
return is_snapshot()
""")

    add("is_testing", "Inside a test", "FALSE until TESTTHAT is set.",
        "is_testing()", "is_testing()", "return is_testing()")

    add("it", "it()", "An it() block is a test.",
        "it a passing expectation",
        'it("ok", { expect_true(TRUE); TRUE })',
        'return it("ok", lambda: expect_true(True))')

    add("local_edition", "Local edition", "The edition is 3 inside the block.",
        "local_edition(3)",
        "local({ local_edition(3); edition_get() })",
        """
with local_edition(3):
    return edition_get()
""")

    add("local_mock", "Defunct local_mock", "Removed in favour of local_mocked_bindings.",
        "local_mock()", "caught(local_mock())", "return caught(lambda: local_mock())")

    add("local_mocked_bindings", "Mock bindings", "Needs a package loaded by pkgload.",
        "local_mocked_bindings(foo = identity)",
        "caught(local_mocked_bindings(foo = identity))",
        "return caught(lambda: local_mocked_bindings(foo=lambda: 1))")

    add("local_mocked_r6_class", "Mock an R6 class", "A string is not an R6 class definition.",
        'local_mocked_r6_class("Foo")',
        'caught(local_mocked_r6_class("Foo"))',
        'return caught(lambda: local_mocked_r6_class("Foo"))')

    add("local_mocked_s3_method", "Mock an S3 method", "The mock is installed and the call returns nothing.",
        'local_mocked_s3_method("print", "foo", function(x) 1)',
        'local_mocked_s3_method("print", "foo", function(x) 1)',
        'return local_mocked_s3_method("print", "foo", lambda x: 1)')

    add("local_mocked_s4_method", "Mock an S4 method", "The mock is installed and the call returns nothing.",
        'local_mocked_s4_method("show", "foo", function(object) 1)',
        'local_mocked_s4_method("show", "foo", function(object) 1)',
        'return local_mocked_s4_method("show", "foo", lambda object: 1)')

    add("local_on_cran", "Pretend to be on CRAN", "NOT_CRAN is false inside the block.",
        "local_on_cran()",
        'local({ local_on_cran(); Sys.getenv("NOT_CRAN") })',
        """
with local_on_cran():
    return os.environ.get("NOT_CRAN")
""")

    add("local_reproducible_output", "Reproducible output", "LANGUAGE is C inside the block.",
        "local_reproducible_output()",
        'local({ local_reproducible_output(); Sys.getenv("LANGUAGE") })',
        """
with local_reproducible_output():
    return os.environ.get("LANGUAGE")
""")

    add("local_snapshotter", "Local snapshotter", "is_snapshot() stays FALSE until a snapshot runs.",
        "local_snapshotter()",
        "local({ local_snapshotter(); is_snapshot() })",
        """
with local_snapshotter():
    return is_snapshot()
""")

    add("local_test_context", "Local test context", "TESTTHAT is true inside the block.",
        "local_test_context()",
        "local({ local_test_context(); is_testing() })",
        """
with local_test_context():
    return is_testing()
""")

    add("local_test_directory", "Local test directory", "The working directory is the given path inside the block.",
        "local_test_directory(temp)",
        """
d <- tempfile(); dir.create(d)
local({ local_test_directory(d); normalizePath(getwd()) == normalizePath(d) })
""",
        """
d = tempfile.mkdtemp()
with local_test_directory(d):
    return os.path.samefile(os.getcwd(), d)
""")

    add("make_expectation", "Make an expectation", "Wrap a condition as an expectation.",
        'make_expectation(new_expectation("success", "ok"))',
        'is.expectation(make_expectation(new_expectation("success", "ok")))',
        'return is_expectation(make_expectation(new_expectation("success", "ok")))')

    add("mock_output_sequence", "Mock a sequence of replies", "The first reply is a.",
        'mock_output_sequence("a", "b")()',
        'mock_output_sequence("a", "b")()',
        'return mock_output_sequence("a", "b")()')

    add("new_expectation", "New expectation", "The class of a success expectation.",
        'new_expectation("success", "ok")',
        'class(new_expectation("success", "ok"))[1]',
        'return "expectation_success" if new_expectation("success", "ok").kind == "success" else ""')

    add("not", "Negate an expectation", "not(equals(2)) passes on 1.",
        "not(equals(2))(1)", "not(equals(2))(1)", "return not_(equals(2))(1)")

    add("pass", "Force a success", "pass() returns nothing.",
        "pass()", "pass()", "return pass_()")

    add("prints_text", "prints_text()", "Old-style output predicate.",
        'prints_text("hi")',
        'prints_text("hi")({ cat("hi"); 1 })',
        """
def f():
    print("hi", end="")
    return 1
return prints_text("hi")(f)
""")

    add("quasi_label", "Quosure label", "A plain value is not a quosure.",
        "quasi_label(1)", "caught(quasi_label(1))", "return caught(lambda: quasi_label(1))")

    add("run_cpp_tests", "Run C++ tests", "xml2 is required and is not used here.",
        'run_cpp_tests("not_a_pkg")',
        'caught(run_cpp_tests("not_a_pkg"))',
        'return caught(lambda: run_cpp_tests("not_a_pkg"))')

    add("set_max_fails", "Maximum failures", "Sys.setenv returns TRUE.",
        "set_max_fails(10)", "set_max_fails(10)", "return set_max_fails(10)")

    add("set_reporter", "Set the reporter", "The active reporter becomes the value that was set.",
        'set_reporter("minimal")',
        """
set_reporter("minimal")
get_reporter()
""",
        """
set_reporter("minimal")
return get_reporter()
""")

    add("set_state_inspector", "State inspector", "The inspector is a function.",
        "set_state_inspector(function() 1)",
        "is.function(set_state_inspector(function() 1))",
        "return callable(set_state_inspector(lambda: 1))")

    add("setup", "setup()", "Code in setup() runs immediately.",
        "setup(1 + 1)", "setup(1 + 1)", "return setup(lambda: 1 + 1)")

    add("show_failure", "Show a failure", "The failure is printed and the call returns nothing.",
        "show_failure(expect_equal(1, 2))",
        "show_failure(expect_equal(1, 2))",
        "return show_failure(lambda: expect_equal(1, 2))")

    add("shows_message", "shows_message()", "Old-style message predicate.",
        'shows_message("hello")',
        'shows_message("hello")(message("hello"))',
        'return shows_message("hello")(lambda: message("hello"))')

    add("simulate_test_env", "Simulate a test environment", "package is required.",
        "simulate_test_env()",
        "caught(simulate_test_env())",
        "return caught(lambda: simulate_test_env())")

    add("skip", "Skip a test", "skip() signals the reason.",
        'skip("skip")', 'caught(skip("skip"))', 'return caught(lambda: skip("skip"))')

    add("skip_if", "Skip if TRUE", "A FALSE condition does not skip.",
        "skip_if(FALSE)", "skip_if(FALSE)", "return skip_if(False)")

    add("skip_if_not", "Skip if not TRUE", "A TRUE condition does not skip.",
        "skip_if_not(TRUE)", "skip_if_not(TRUE)", "return skip_if_not(True)")

    add("skip_if_not_installed", "Skip if missing", "jsonlite is installed on both sides.",
        'skip_if_not_installed("jsonlite")',
        'skip_if_not_installed("jsonlite")',
        'return skip_if_not_installed("jsonlite")')

    add("skip_if_offline", "Skip if offline", "Without curl, the check stops before the network.",
        "skip_if_offline()",
        "caught(skip_if_offline())",
        "return caught(lambda: skip_if_offline())")

    add("skip_if_translated", "Skip if translated", "An English message is not skipped.",
        'skip_if_translated("x")',
        'skip_if_translated("x")',
        'return skip_if_translated("x")')

    add("skip_on_appveyor", "Skip on Appveyor", "Not on Appveyor.",
        "skip_on_appveyor()",
        """
Sys.unsetenv("APPVEYOR")
skip_on_appveyor()
""",
        """
os.environ.pop("APPVEYOR", None)
return skip_on_appveyor()
""")

    add("skip_on_bioc", "Skip on Bioconductor", "Not on a Bioconductor builder.",
        "skip_on_bioc()",
        """
Sys.unsetenv("IS_BIOC_BUILD_MACHINE")
skip_on_bioc()
""",
        """
os.environ.pop("IS_BIOC_BUILD_MACHINE", None)
return skip_on_bioc()
""")

    add("skip_on_ci", "Skip on CI", "CI is cleared, so the test runs.",
        "skip_on_ci()",
        """
Sys.unsetenv("CI")
skip_on_ci()
""",
        """
os.environ.pop("CI", None)
return skip_on_ci()
""")

    add("skip_on_covr", "Skip under covr", "Not under covr.",
        "skip_on_covr()",
        """
Sys.unsetenv("R_COVR")
skip_on_covr()
""",
        """
os.environ.pop("R_COVR", None)
return skip_on_covr()
""")

    add("skip_on_cran", "Skip on CRAN", "NOT_CRAN=true means the test runs.",
        "skip_on_cran()",
        """
Sys.setenv(NOT_CRAN = "true")
skip_on_cran()
""",
        """
os.environ["NOT_CRAN"] = "true"
return skip_on_cran()
""")

    add("skip_on_os", "Skip on an operating system", "Windows is not this host, so the call returns TRUE.",
        'skip_on_os("windows")',
        'skip_on_os("windows")',
        'return skip_on_os("windows")')

    add("skip_on_travis", "Skip on Travis", "Not on Travis.",
        "skip_on_travis()",
        """
Sys.unsetenv("TRAVIS")
skip_on_travis()
""",
        """
os.environ.pop("TRAVIS", None)
return skip_on_travis()
""")

    add("skip_unless_r", "Skip unless R is new enough", "R 4.5 satisfies >= 4.0.0.",
        'skip_unless_r(">= 4.0.0")',
        'skip_unless_r(">= 4.0.0")',
        'return skip_unless_r(">= 4.0.0")')

    add("snapshot_accept", "Accept snapshots", "Nothing to update.",
        "snapshot_accept()", "snapshot_accept()", "return snapshot_accept()")

    add("snapshot_download_gh", "Download snapshots", "run_id is required once the repository is set.",
        'snapshot_download_gh("r-lib/testthat")',
        'caught(snapshot_download_gh("r-lib/testthat"))',
        'return caught(lambda: snapshot_download_gh("r-lib/testthat"))')

    add("snapshot_reject", "Reject snapshots", "Nothing to reject.",
        "snapshot_reject()", "snapshot_reject()", "return snapshot_reject()")

    add("snapshot_review", "Review snapshots", "shiny and diffviewer are required.",
        "snapshot_review()", "caught(snapshot_review())", "return caught(lambda: snapshot_review())")

    add("source_dir", "Source a directory", "An empty directory sources nothing.",
        "length(source_dir(empty))",
        """
d <- tempfile(); dir.create(d)
length(source_dir(d))
""",
        """
d = tempfile.mkdtemp()
return len(source_dir(d))
""")

    add("source_file", "Source a file", "A missing path is rejected.",
        'source_file("no-such-file.R")',
        'caught(source_file("no-such-file.R"))',
        'return caught(lambda: source_file("no-such-file.R"))')

    add("source_test_helpers", "Source helpers", "An empty directory has no helpers.",
        "length(source_test_helpers(empty))",
        """
d <- tempfile(); dir.create(d)
length(source_test_helpers(d))
""",
        """
d = tempfile.mkdtemp()
return len(source_test_helpers(d))
""")

    add("source_test_setup", "Source setup", "An empty directory has no setup file.",
        "length(source_test_setup(empty))",
        """
d <- tempfile(); dir.create(d)
length(source_test_setup(d))
""",
        """
d = tempfile.mkdtemp()
return len(source_test_setup(d))
""")

    add("source_test_teardown", "Source teardown", "An empty directory has no teardown file.",
        "length(source_test_teardown(empty))",
        """
d <- tempfile(); dir.create(d)
length(source_test_teardown(d))
""",
        """
d = tempfile.mkdtemp()
return len(source_test_teardown(d))
""")

    add("succeed", "Force a success message", "succeed() returns an expectation.",
        'succeed("ok")',
        'is.expectation(succeed("ok"))',
        'return is_expectation(succeed("ok"))')

    add("takes_less_than", "Time limit", "Evaluating 1 takes less than 10 seconds.",
        "takes_less_than(10)(1)", "takes_less_than(10)(1)", "return takes_less_than(10)(1)")

    add("teardown", "teardown()", "The handler is queued and the call returns nothing.",
        "teardown(1)", "teardown(1)", "return teardown(lambda: 1)")

    add("teardown_env", "Teardown environment", "Uninitialized until a test file starts.",
        "teardown_env()", "caught(teardown_env())", "return caught(lambda: teardown_env())")

    add("test_check", "R CMD check entry", "The installed package has no DESCRIPTION to check.",
        'test_check("not_a_pkg")',
        'caught(test_check("not_a_pkg"))',
        'return caught(lambda: test_check("not_a_pkg"))')

    add("test_dir", "Run a directory", "An empty directory has no test files.",
        "test_dir(empty)",
        """
d <- tempfile(); dir.create(d)
caught(test_dir(d))
""",
        """
d = tempfile.mkdtemp()
return caught(lambda: test_dir(d))
""")

    add("test_env", "Test environment", "A fresh environment for a test file.",
        "test_env()", "is.environment(test_env())", "return isinstance(test_env(), dict)")

    add("test_example", "Run one example", "An Rd file is not a Python example.",
        'test_example("nope.Rd")',
        'caught(test_example("nope.Rd"))',
        'return caught(lambda: test_example("nope.Rd"))')

    add("test_examples", "Run examples", "The path does not exist.",
        'test_examples("nope")',
        'caught(test_examples("nope"))',
        'return caught(lambda: test_examples("nope"))')

    add("test_file", "Run one file", "The path does not exist.",
        'test_file("missing.py")',
        'caught(test_file("missing.py"))',
        'return caught(lambda: test_file("missing.py"))')

    add("test_local", "Run local tests", "The directory has no DESCRIPTION.",
        'test_local("/tmp/no-such-tt-dir")',
        'caught(test_local("/tmp/no-such-tt-dir"))',
        'return caught(lambda: test_local("/tmp/no-such-tt-dir"))')

    add("test_package", "Run an installed package", "not_a_pkg has no installed tests.",
        'test_package("not_a_pkg")',
        'test_package("not_a_pkg")',
        'return test_package("not_a_pkg")')

    add("test_path", "Path inside tests", "tests/testthat is not here.",
        'test_path("a")',
        'caught(test_path("a"))',
        'return caught(lambda: test_path("a"))')

    add("test_rd", "Run an Rd file", "The file cannot be opened.",
        'test_rd("nope")',
        'caught(test_rd("nope"))',
        'return caught(lambda: test_rd("nope"))')

    add("test_that", "One test", "A passing expectation makes the test succeed.",
        'test_that("ok", expect_equal(1, 1))',
        'test_that("ok", { expect_equal(1, 1); TRUE })',
        'return test_that("ok", lambda: expect_equal(1, 1))')

    add("testing_package", "Package under test", "TESTTHAT_PKG names the package.",
        "testing_package()",
        """
Sys.setenv(TESTTHAT_PKG = "demo")
testing_package()
""",
        """
os.environ["TESTTHAT_PKG"] = "demo"
return testing_package()
""")

    add("testthat_example", "Example file", "The built-in success example.",
        'basename(testthat_example("success"))',
        'basename(testthat_example("success"))',
        'return os.path.basename(testthat_example("success"))')

    add("testthat_examples", "Example directory", "The directory is named examples.",
        "basename(testthat_examples())",
        "basename(testthat_examples())",
        "return os.path.basename(testthat_examples())")

    add("testthat_print", "Print a value", "The value is returned.",
        "testthat_print(3)", "testthat_print(3)", "return testthat_print(3)")

    add("testthat_tolerance", "Numeric tolerance", "sqrt(.Machine$double.eps).",
        "testthat_tolerance()", "testthat_tolerance()", "return testthat_tolerance()")

    add("throws_error", "throws_error()", "Old-style error predicate.",
        'throws_error("boom")',
        'conditionMessage(throws_error("boom")(stop("boom")))',
        'return str(throws_error("boom")(lambda: (_ for _ in ()).throw(RuntimeError("boom"))))')

    add("try_again", "Retry", "A value that does not fail is returned.",
        "try_again(2, 5)", "try_again(2, 5)", "return try_again(2, lambda: 5)")

    add("use_catch", "Catch scaffold", "The directory has no DESCRIPTION.",
        'use_catch("not_a_pkg")',
        'caught(use_catch("not_a_pkg"))',
        'return caught(lambda: use_catch("not_a_pkg"))')

    add("verify_output", "Verify printed output", "The first call writes a reference.",
        "verify_output(tempfile, 1)",
        'caught(verify_output(tempfile(), "hello"))',
        'return caught(lambda: verify_output(tempfile.mktemp(), lambda: print("hello")))')

    add("watch", "Watch files", "path is required.",
        "watch()", "caught(watch())", "return caught(lambda: watch())")

    add("with_mock", "Defunct with_mock", "Removed in favour of with_mocked_bindings.",
        "with_mock(1)", "caught(with_mock(1))", "return caught(lambda: with_mock(1))")

    add("with_mocked_bindings", "Mock for one call", "Needs a package loaded by pkgload.",
        "with_mocked_bindings(1)",
        "caught(with_mocked_bindings(1 + 1, x = 2))",
        "return caught(lambda: with_mocked_bindings(lambda: 2, x=2))")

    add("with_reporter", "Run with a reporter", "The active reporter is returned.",
        "with_reporter(MinimalReporter, 7)",
        "class(with_reporter(MinimalReporter$new(), 7))[1]",
        """
with with_reporter(MinimalReporter()) as reporter:
    _ = 7
return type(reporter).__name__
""")

    order = [
        "%>%", "CheckReporter", "CompactProgressReporter", "DebugReporter", "FailReporter",
        "JunitReporter", "ListReporter", "LlmReporter", "LocationReporter", "MinimalReporter",
        "MultiReporter", "ParallelProgressReporter", "ProgressReporter", "RStudioReporter",
        "Reporter", "SilentReporter", "SlowReporter", "StopReporter", "SummaryReporter",
        "TapReporter", "TeamcityReporter", "announce_snapshot_file", "auto_test",
        "auto_test_package", "capture_condition", "capture_error", "capture_expectation",
        "capture_message", "capture_messages", "capture_output", "capture_output_lines",
        "capture_warning", "capture_warnings", "check_reporter", "compare",
        "compare_file_binary", "compare_file_text", "context", "context_start_file",
        "default_compact_reporter", "default_reporter", "describe", "edition_get", "equals",
        "equals_reference", "evaluate_promise", "expect", "expect_all_equal", "expect_all_false",
        "expect_all_true", "expect_condition", "expect_contains", "expect_cpp_tests_pass",
        "expect_disjoint", "expect_equal", "expect_equal_to_reference", "expect_equivalent",
        "expect_error", "expect_failure", "expect_false", "expect_gt", "expect_gte",
        "expect_identical", "expect_in", "expect_invisible", "expect_is", "expect_known_hash",
        "expect_known_output", "expect_known_value", "expect_length", "expect_less_than",
        "expect_lt", "expect_lte", "expect_mapequal", "expect_match", "expect_message",
        "expect_more_than", "expect_named", "expect_no_condition", "expect_no_error",
        "expect_no_failure", "expect_no_match", "expect_no_message", "expect_no_success",
        "expect_no_warning", "expect_null", "expect_output", "expect_output_file",
        "expect_r6_class", "expect_reference", "expect_s3_class", "expect_s4_class",
        "expect_s7_class", "expect_setequal", "expect_shape", "expect_silent", "expect_snapshot",
        "expect_snapshot_error", "expect_snapshot_failure", "expect_snapshot_file",
        "expect_snapshot_output", "expect_snapshot_value", "expect_snapshot_warning",
        "expect_success", "expect_that", "expect_true", "expect_type", "expect_vector",
        "expect_visible", "expect_warning", "expectation", "exp_signal", "extract_test", "fail",
        "find_test_scripts", "get_reporter", "gives_warning", "has_names", "is.expectation",
        "is_a", "is_checking", "is_equivalent_to", "is_identical_to", "is_informative_error",
        "is_less_than", "is_more_than", "is_parallel", "is_snapshot", "is_testing", "it",
        "local_edition", "local_mock", "local_mocked_bindings", "local_mocked_r6_class",
        "local_mocked_s3_method", "local_mocked_s4_method", "local_on_cran",
        "local_reproducible_output", "local_snapshotter", "local_test_context",
        "local_test_directory", "make_expectation", "mock_output_sequence", "new_expectation",
        "not", "pass", "prints_text", "quasi_label", "run_cpp_tests", "set_max_fails",
        "set_reporter", "set_state_inspector", "setup", "show_failure", "shows_message",
        "simulate_test_env", "skip", "skip_if", "skip_if_not", "skip_if_not_installed",
        "skip_if_offline", "skip_if_translated", "skip_on_appveyor", "skip_on_bioc",
        "skip_on_ci", "skip_on_covr", "skip_on_cran", "skip_on_os", "skip_on_travis",
        "skip_unless_r", "snapshot_accept", "snapshot_download_gh", "snapshot_reject",
        "snapshot_review", "source_dir", "source_file", "source_test_helpers",
        "source_test_setup", "source_test_teardown", "succeed", "takes_less_than", "teardown",
        "teardown_env", "test_check", "test_dir", "test_env", "test_example", "test_examples",
        "test_file", "test_local", "test_package", "test_path", "test_rd", "test_that",
        "testing_package", "testthat_example", "testthat_examples", "testthat_print",
        "testthat_tolerance", "throws_error", "try_again", "use_catch", "verify_output",
        "watch", "with_mock", "with_mocked_bindings", "with_reporter",
    ]
    by_name = {item["name"]: item for item in out}
    missing = [name for name in order if name not in by_name]
    extra = [item["name"] for item in out if item["name"] not in order]
    if missing or extra or len(by_name) != len(out):
        raise SystemExit(f"missing={missing} extra={extra} dup={len(out) - len(by_name)}")
    return [by_name[name] for name in order]


def _r_script(item: dict, example: bool) -> str:
    body = textwrap.indent(item["r"], "  ")
    if example:
        return (
            "suppressPackageStartupMessages(library(testthat))\n"
            + "caught <- function(expr) {\n"
            + "  tryCatch(expr, error = function(e) conditionMessage(e), skip = function(e) conditionMessage(e))\n"
            + "}\n"
            + R_SHOW
            + f"one <- function() {{\n{body}\n}}\nshow(one())\n"
        )
    return (
        "suppressPackageStartupMessages(library(testthat))\n"
        + R_HELPER
        + f"one <- function() {{\n{body}\n}}\n"
        + "value <- one()\n"
        + "elapsed <- numeric(20)\n"
        + "for (i in seq_len(20)) {\n"
        + "  t0 <- as.numeric(Sys.time())\n"
        + "  one()\n"
        + "  elapsed[[i]] <- as.numeric(Sys.time()) - t0\n"
        + "}\n"
        + 'cat(sprintf("{\\"value\\":%s,\\"median_ms\\":%.17g}\\n", to_json(value), median(elapsed) * 1000))\n'
    )


def _py_script(item: dict, example: bool) -> str:
    body = textwrap.indent(item["py"], "    ")
    header = (
        "import os\nimport tempfile\nimport warnings\n"
        "warnings.filterwarnings('ignore')\n"
        "from testthat import *\n"
        "def caught(fn):\n"
        "    try:\n"
        "        fn()\n"
        "        return ''\n"
        "    except Exception as exc:\n"
        "        return str(exc)\n"
    )
    if example:
        return header + PY_SHOW + f"def one():\n{body}\nshow(one())\n"
    return (
        "import json\nimport os\nimport statistics\nimport tempfile\nimport time\nimport warnings\n"
        "warnings.filterwarnings('ignore')\n"
        "from testthat import *\n"
        "def caught(fn):\n"
        "    try:\n"
        "        fn()\n"
        "        return ''\n"
        "    except Exception as exc:\n"
        "        return str(exc)\n"
        + f"def one():\n{body}\n"
        + "value = one()\n"
        + "elapsed = []\n"
        + "for _ in range(20):\n"
        + "    started = time.perf_counter()\n"
        + "    one()\n"
        + "    elapsed.append((time.perf_counter() - started) * 1000)\n"
        + "print(json.dumps({\"value\": value, \"median_ms\": statistics.median(elapsed)}))\n"
    )


def _run(argv: list[str], script: str) -> tuple[str, str, int]:
    result = subprocess.run(argv, input=script, text=True, capture_output=True, cwd="/tmp")
    return result.stdout, result.stderr, result.returncode


def _diff(left, right) -> tuple[bool, float]:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right, 0.0 if left == right else 1.0
    if isinstance(left, (int, float)) and isinstance(right, (int, float)) and not isinstance(left, bool) and not isinstance(right, bool):
        delta = abs(float(left) - float(right))
        return delta <= 1e-8, delta
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        ok = True
        worst = 0.0
        for a, b in zip(left, right):
            matched, delta = _diff(a, b)
            ok = ok and matched
            worst = max(worst, delta)
        return ok, worst
    return left == right, 0.0 if left == right else 1.0


def _doc(item: dict) -> dict:
    arguments = [{"name": name, "text": text} for name, text in item.get("arguments") or []]
    name = item["name"]
    py = PY_NAMES.get(name, name)
    description = item["description"]
    return {
        "name": name,
        "title": item["title"],
        "origin": {
            "description": description,
            "usage": f"{name}(...)",
            "arguments": arguments,
            "details": description,
            "value": "See the example.",
            "example": item["r"].strip() + "\n",
            "output": f"output/{name}-r.txt",
        },
        "translation": {
            "description": description,
            "usage": f"{py}(...)",
            "arguments": arguments,
            "details": description + " code is a callable. local_* is a context manager.",
            "value": "See the example.",
            "example": "from testthat import *\n\n" + item["py"].strip() + "\n",
            "output": f"output/{name}-python.txt",
        },
    }


def _function(item: dict, check: dict) -> dict:
    name = item["name"]
    py = PY_NAMES.get(name, name)
    return {
        "name": name,
        "translated": True,
        "python": f"testthat.{py}",
        "loads": item.get("loads") or [],
        "uses": item.get("uses") or [],
        "done": item["description"],
        "not_done": "",
        "blocked_by": [],
        "assigned": "",
        "check": check,
    }


def main() -> None:
    items = cases()
    only = os.environ.get("ONLY", "")
    if only:
        items = [item for item in items if item["name"] in only.split(",")]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    PROOF.mkdir(parents=True, exist_ok=True)
    functions = []
    failed = []
    for item in items:
        r_proof = _r_script(item, example=False)
        py_proof = _py_script(item, example=False)
        r_example = _r_script(item, example=True)
        py_example = _py_script(item, example=True)
        safe = item["name"].replace("%>%", "pipe").replace(".", "_")
        r_out, r_err, r_code = _run(["Rscript", "-"], r_proof)
        py_out, py_err, py_code = _run([str(PY), "-"], py_proof)
        (PROOF / f"{safe}-r.R").write_text(r_proof)
        (PROOF / f"{safe}-py.py").write_text(py_proof)
        if r_code != 0 or py_code != 0:
            failed.append(item["name"])
            print(f"FAIL {item['name']} run r={r_code} py={py_code}")
            if r_err:
                print(r_err[-400:])
            if py_err:
                print(py_err[-400:])
            if r_out:
                print("ROUT", r_out[-200:])
            continue
        line_r = next((line for line in reversed(r_out.splitlines()) if line.startswith("{")), "")
        line_py = next((line for line in reversed(py_out.splitlines()) if line.startswith("{")), "")
        try:
            r_payload = json.loads(line_r)
            py_payload = json.loads(line_py)
        except json.JSONDecodeError:
            failed.append(item["name"])
            print(f"FAIL {item['name']} json")
            print("R", r_out[-300:])
            print("PY", py_out[-300:])
            continue
        matched, delta = _diff(r_payload["value"], py_payload["value"])
        if not matched:
            failed.append(item["name"])
            print(f"FAIL {item['name']} value r={r_payload['value']!r} py={py_payload['value']!r}")
        r_ms = float(r_payload["median_ms"])
        py_ms = float(py_payload["median_ms"])
        ex_r, ex_r_err, ex_r_code = _run(["Rscript", "-"], r_example)
        ex_py, ex_py_err, ex_py_code = _run([str(PY), "-"], py_example)
        if ex_r_code != 0 or ex_py_code != 0:
            failed.append(item["name"])
            print(f"FAIL {item['name']} example r={ex_r_code} py={ex_py_code}")
            if ex_r_err:
                print(ex_r_err[-300:])
            if ex_py_err:
                print(ex_py_err[-300:])
        (OUTPUT / f"{safe}-r.txt").write_text(ex_r if ex_r.endswith("\n") or not ex_r else ex_r + "\n")
        (OUTPUT / f"{safe}-python.txt").write_text(ex_py if ex_py.endswith("\n") or not ex_py else ex_py + "\n")
        doc = _doc(item)
        doc["origin"]["output"] = f"output/{safe}-r.txt"
        doc["translation"]["output"] = f"output/{safe}-python.txt"
        (DOCS / f"{safe}.json").write_text(json.dumps(doc, indent=2) + "\n")
        functions.append(_function(item, {
            "case": item["story"],
            "r_ms": r_ms,
            "translated_ms": py_ms,
            "speedup": (r_ms / py_ms) if py_ms else None,
            "matches": matched,
            "max_abs_diff": delta,
            "tolerance": 1e-8,
            "proof": {"r": r_proof, "python": py_proof},
        }))
        mark = "ok" if matched else "DIFF"
        print(f"{mark} {item['name']} speedup={r_ms / py_ms if py_ms else 0:.3f}")
    if only:
        path = ROOT / "translation.json"
        if path.exists() and functions:
            record = json.loads(path.read_text())
            by_name = {item["name"]: item for item in record.get("functions", [])}
            for item in functions:
                by_name[item["name"]] = item
            order = [item["name"] for item in cases()]
            record["functions"] = [by_name[name] for name in order if name in by_name]
            still = [item["name"] for item in record["functions"] if not item["check"]["matches"]]
            record["status"] = "complete" if not still and len(record["functions"]) == 207 else "in_progress"
            if record["status"] == "complete":
                record["resume"] = (
                    "All 207 exports of testthat 3.3.2 are checked. code is a callable, and local_* is a context manager. "
                    "Edition 2 is the default outside a package. Equality in edition 3 uses the waldo-style slice in this package. "
                    "brio, callr, desc, evaluate, lifecycle, pkgload, praise, processx, ps, R6, rlang, and waldo stay untranslated. "
                    "The Catch runner stays out."
                )
            else:
                record["resume"] = f"{len(record['functions'])} of 207 exports checked. {len(still)} still differ."
            path.write_text(json.dumps(record, indent=2) + "\n")
        print(f"only={only} failed={failed}")
        if failed:
            raise SystemExit(1)
        return
    record = {
        "name": "testthat",
        "cran_version": "3.3.2",
        "inventory": "complete",
        "status": "complete" if not failed and len(functions) == 207 else "in_progress",
        "blocked_by": [],
        "crate_claims": [],
        "resume": (
            "All 207 exports of testthat 3.3.2 are checked. code is a callable, and local_* is a context manager. "
            "Edition 2 is the default outside a package. Equality in edition 3 uses the waldo-style slice in this package. "
            "brio, callr, desc, evaluate, lifecycle, pkgload, praise, processx, ps, R6, rlang, and waldo stay untranslated. "
            "The Catch runner stays out."
        ),
        "functions": functions,
    }
    if failed or len(functions) != 207:
        record["status"] = "in_progress"
        record["resume"] = f"{len(functions)} of 207 exports checked. {len(failed)} still differ."
    (ROOT / "translation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote translation.json status={record['status']} failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
