"""Edges for stringi's join functions, including a check against R."""

import json
import math
import os
import subprocess
import tempfile
import warnings

import pytest

from stringi._na import NA
from stringi.join import (
    stri_c,
    stri_c_list,
    stri_dup,
    stri_flatten,
    stri_join,
    stri_join_list,
    stri_paste,
    stri_paste_list,
)


def test_aliases_are_the_same_functions():
    assert stri_c is stri_join
    assert stri_paste is stri_join
    assert stri_c_list is stri_join_list
    assert stri_paste_list is stri_join_list


def test_known_results():
    assert stri_dup(["a", NA], 2) == ["aa", NA]
    assert stri_dup("NA", 2) == ["NANA"]
    assert stri_join([1, 2, 3], ["a", "b", "c"], sep="-") == ["1-a", "2-b", "3-c"]
    assert stri_c([1, 2, 3], ["a", "b", "c"], sep="-") == ["1-a", "2-b", "3-c"]
    assert stri_paste(["a", NA], ["x", "y"], sep="-") == ["a-x", NA]


def test_dup_edges():
    assert stri_dup("a", range(1, 6)) == ["a", "aa", "aaa", "aaaa", "aaaaa"]
    assert stri_dup(["a", NA, "ba"], 4) == ["aaaa", NA, "babababa"]
    assert stri_dup(["abc", "pqrst"], [4, 2]) == ["abcabcabcabc", "pqrstpqrst"]
    assert stri_dup("ab", 0) == [""]
    assert stri_dup("ab", -1) == [NA]
    assert stri_dup("ab", NA) == [NA]
    assert stri_dup(NA, 0) == [NA]
    assert stri_dup("", 3) == [""]
    assert stri_dup("", -1) == [NA]
    assert stri_dup([], 2) == []
    assert stri_dup("a", []) == []
    assert stri_dup(None, 2) == []
    assert stri_dup("a", None) == []
    assert stri_dup("ab", 2.9) == ["abab"]
    assert stri_dup("ab", -1.2) == [NA]
    assert stri_dup("ab", 0.9) == [""]
    assert stri_dup("ab", -0.9) == [""]
    assert stri_dup([True, False, NA], 2) == ["TRUETRUE", "FALSEFALSE", NA]
    assert stri_dup([1, NA, 1.5], 2) == ["11", NA, "1.51.5"]
    assert stri_dup("ab", True) == ["ab"]
    assert stri_dup("ab", False) == [""]
    assert stri_dup("ą", 3) == ["ąąą"]
    assert stri_dup("a", "2") == ["aa"]
    assert stri_dup("ab", "2.9") == ["abab"]
    assert stri_dup("a", "+3") == ["aaa"]
    assert stri_dup("a", " 2") == ["aa"]
    assert stri_dup("ab", "0x2") == ["abab"]


def test_dup_warnings_and_limits():
    with pytest.warns(UserWarning, match="not a multiple"):
        assert stri_dup(["a", "b", "c"], [1, 2]) == ["a", "bb", "c"]
    with pytest.warns(UserWarning, match="integer range"):
        assert stri_dup("a", math.inf) == [NA]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert stri_dup("a", math.nan) == [NA]
        assert stri_dup("a", "x") == [NA]
    messages = [str(item.message) for item in caught]
    assert "NAs introduced by coercion to integer range" not in messages[:1]
    assert any(str(item.message) == "NAs introduced by coercion" for item in caught)
    with pytest.raises(ValueError, match="2\\^31-1"):
        stri_dup("a" * 1000, 3_000_000)


def test_join_edges():
    assert stri_join(["a", NA, "c"], ["x", "y", "z"], sep="-") == ["a-x", NA, "c-z"]
    assert stri_join(["NA", "a"], "b") == ["NAb", "ab"]
    assert stri_join(["a", "b"], [], "c") == []
    assert stri_join(["a", "b"], [], "c", ignore_null=True) == ["ac", "bc"]
    assert stri_join() == []
    assert stri_join(collapse=",") == [""]
    assert stri_join(collapse=NA) == [""]
    assert stri_join(collapse=[]) == [""]
    assert stri_join([], [], ignore_null=True) == []
    assert stri_join([], collapse=",", ignore_null=True) == [""]
    assert stri_join(["a", NA, "b"]) == ["a", NA, "b"]
    assert stri_join(["a", NA, "b"], collapse=",") == [NA]
    assert stri_join(["a", NA], ["x", "y"], collapse="-") == [NA]
    assert stri_join(["a", "b"], ["x", "y"], sep=NA) == [NA, NA]
    assert stri_join(["a", "b"], ["x", "y"], sep=NA, collapse=",") == [NA]
    assert stri_join(["a", "b"], collapse=NA) == [NA]
    assert stri_join(["a", ""], ["b", "c"], sep="-") == ["a-b", "-c"]
    assert stri_join([True, False, NA], "x") == ["TRUEx", "FALSEx", NA]
    assert stri_join(
        [0.0001, 100000.0, NA, math.nan, math.inf, -math.inf], "z", sep="|"
    ) == ["1e-04|z", "1e+05|z", NA, "NaN|z", "Inf|z", "-Inf|z"]
    assert stri_join("a", "b", "c", sep="-") == ["a-b-c"]
    assert stri_join(["a", "b", "c"], collapse="") == ["abc"]
    assert stri_join(["a", NA], ["x", "y"], sep="", collapse="-") == [NA]
    assert stri_join([], collapse=",") == [""]
    assert stri_join([]) == []
    assert stri_join([1, NA, 3], "x", sep="-") == ["1-x", NA, "3-x"]
    assert stri_join("a", "b", sep=1) == ["a1b"]
    assert stri_join(["a", "b"], collapse=False) == ["aFALSEb"]
    assert stri_join(None, ["a", "b"]) == []
    assert stri_join(None, ["a", "b"], ignore_null=True) == ["a", "b"]
    assert stri_join(["a", "b"], sep="-") == ["a", "b"]
    assert stri_join(["a", "b"], sep="XXX", collapse=",") == ["a,b"]
    assert stri_join(["a", "b"], [], collapse=",") == [""]
    assert stri_join(["a", "b"], [], collapse=NA) == [NA]
    assert stri_join(["a", "b"], [], sep=NA, collapse=",") == [NA]
    assert stri_join([], collapse=NA) == [NA]
    assert stri_join(["a", "b"], ["x", "y"], sep="", collapse="-") == ["ax-by"]
    assert stri_join(["a", "b"], ["x", "y"], sep="-", collapse="|") == ["a-x|b-y"]
    assert stri_join("ą", "ę", sep="-") == ["ą-ę"]
    assert stri_join(["a", "b"], "x", sep="-") == ["a-x", "b-x"]


def test_join_warnings_and_errors():
    with pytest.warns(UserWarning, match="not a multiple"):
        assert stri_join(["a", "b"], ["x", "y", "z"], sep="-") == ["a-x", "b-y", "a-z"]
    with pytest.warns(UserWarning, match="single character string"):
        assert stri_join(["a", "b"], ["x", "y"], sep=["-", "+"]) == ["a-x", "b-y"]
    with pytest.warns(UserWarning, match="single logical"):
        assert stri_join("a", "b", ignore_null=[True, False]) == ["ab"]
    with pytest.raises(ValueError, match="argument `sep` should be a non-empty vector"):
        stri_join("a", "b", sep=[])
    with pytest.raises(ValueError, match="argument `collapse` should be a non-empty vector"):
        stri_join("a", "b", collapse=[])
    with pytest.raises(ValueError, match="missing values in argument `ignore_null`"):
        stri_join("a", ignore_null=NA)
    with pytest.raises(ValueError, match="argument `sep` should be a non-empty vector"):
        stri_join("a", "b", sep=None)


def test_flatten_edges():
    assert stri_flatten(list("ABC"), collapse=",") == ["A,B,C"]
    assert stri_flatten([]) == [""]
    assert stri_flatten([], collapse=",") == [""]
    assert stri_flatten(None) == [""]
    assert stri_flatten(["a", NA, "b"], collapse=",") == [NA]
    assert stri_flatten(["a", NA, "b"], collapse=",", na_empty=True) == ["a,,b"]
    assert stri_flatten(["a", NA, "b"], collapse=",", na_empty=NA) == ["a,b"]
    assert stri_flatten(["a", "", "b"], collapse=",", omit_empty=True) == ["a,b"]
    assert stri_flatten(
        [NA, "", "A", "", "B", NA, "C"],
        collapse=",",
        na_empty=True,
        omit_empty=True,
    ) == ["A,B,C"]
    assert stri_flatten(
        [NA, "", "A", "", "B", NA, "C"], collapse=",", na_empty=NA
    ) == [",A,,B,C"]
    assert stri_flatten(
        [NA, "", "A", "", "B", NA, "C"],
        collapse=",",
        na_empty=NA,
        omit_empty=True,
    ) == ["A,B,C"]
    assert stri_flatten([NA, "", "A"], collapse=",", na_empty=False, omit_empty=True) == [NA]
    assert stri_flatten(["a", "", "b", NA], collapse="", omit_empty=True) == [NA]
    assert stri_flatten(["a", "", "b"], collapse="", omit_empty=True) == ["ab"]
    assert stri_flatten(["a", NA, "b"], collapse="", na_empty=True) == ["ab"]
    assert stri_flatten(["a", NA, "", "b"], collapse="", na_empty=NA, omit_empty=True) == ["ab"]
    assert stri_flatten(["a", "b"], collapse=NA) == [NA]
    assert stri_flatten("a", collapse=",") == ["a"]
    assert stri_flatten(["", ""], collapse=",", omit_empty=True) == [""]
    assert stri_flatten([NA, NA], collapse=",", na_empty=True, omit_empty=True) == [""]
    assert stri_flatten([NA, NA], collapse=",", na_empty=NA) == [""]
    assert stri_flatten([NA, NA], collapse=",", na_empty=True) == [","]
    assert stri_flatten(NA, collapse=",") == [NA]
    assert stri_flatten(["", "a", "", "b", ""], collapse="|", omit_empty=True) == ["a|b"]
    assert stri_flatten([NA, "a", NA, "b"], collapse="|", na_empty=True) == ["|a||b"]
    assert stri_flatten([NA, "a"], collapse="|", na_empty=True) == ["|a"]
    assert stri_flatten(["NA", "a"], collapse=",") == ["NA,a"]
    assert stri_flatten([1, 2, 3], collapse="-") == ["1-2-3"]
    assert stri_flatten(["", NA], collapse=",", na_empty=True, omit_empty=True) == [""]
    assert stri_flatten(["", "a", ""], collapse=",", na_empty=NA) == [",a,"]
    assert stri_flatten([NA], collapse=",", na_empty=True) == [""]
    assert stri_flatten([NA], collapse="", na_empty=True) == [""]
    assert stri_flatten([], collapse=NA) == [NA]


def test_flatten_warnings_and_errors():
    with pytest.warns(UserWarning, match="single character string"):
        assert stri_flatten(["a", "b"], collapse=[",", "+"]) == ["a,b"]
    with pytest.warns(UserWarning, match="single logical"):
        assert stri_flatten(["a", "b"], collapse=",", na_empty=[True, False]) == ["a,b"]
    with pytest.warns(UserWarning, match="single logical"):
        assert stri_flatten(["a", ""], collapse=",", omit_empty=[True, False]) == ["a"]
    assert stri_flatten("a", na_empty="TRUE") == ["a"]
    assert stri_flatten(["a", NA], collapse=",", na_empty="TRUE") == ["a,"]
    assert stri_flatten(["a", NA], collapse=",", na_empty="T") == ["a,"]
    assert stri_flatten(["a", NA], collapse=",", na_empty=1) == ["a,"]
    assert stri_flatten(["a", NA], collapse=",", na_empty=0) == [NA]
    assert stri_flatten(["a", ""], collapse=",", omit_empty="TRUE") == ["a"]
    with pytest.raises(ValueError, match="missing values in argument `omit_empty`"):
        stri_flatten("a", omit_empty=NA)
    with pytest.raises(ValueError, match="argument `collapse` should be a non-empty vector"):
        stri_flatten("a", collapse=[])
    with pytest.raises(ValueError, match="non-empty"):
        stri_flatten("a", na_empty=[])


def test_join_list_edges():
    assert stri_join_list(
        [["a", "b"], ["c", NA], [], ["d"]], sep="-"
    ) == ["a-b", NA, "d"]
    assert stri_join_list(
        [["a", "b"], ["c", NA], [], ["d"]], sep="-", collapse="|"
    ) == [NA]
    assert stri_join_list([], sep=",") == []
    assert stri_join_list([], collapse=",") == []
    assert stri_join_list([], sep=[]) == []
    assert stri_join_list([[], None], sep=",") == []
    assert stri_join_list([["a", "b"], ["c", "d"]], sep=NA) == [NA, NA]
    assert stri_join_list([["a", "b"]], sep=NA, collapse=",") == [NA]
    assert stri_join_list([["a", "b"], ["c"]], collapse=NA) == [NA]
    assert stri_join_list([["a", NA], ["b"]], sep=",", collapse="|") == [NA]
    assert stri_join_list([["a", ""]], sep="-") == ["a-"]
    assert stri_join_list([["a", "b"], ["c"]], sep="", collapse="") == ["abc"]
    assert stri_join_list([[1, 2, 3], [4, 5]], sep=",") == ["1,2,3", "4,5"]
    assert stri_join_list(["a", "b"], sep="") == ["a", "b"]
    assert stri_join_list(["a", "b"], sep="-") == ["a", "b"]
    assert stri_c_list([["a", "b"]], sep="-") == ["a-b"]
    assert stri_paste_list([["a", "b"], ["c"]], collapse="|") == ["ab|c"]
    assert stri_join_list([["a", NA, "b"]], sep="") == [NA]
    assert stri_join_list([["a", "", "b"]], sep="") == ["ab"]


def test_join_list_warnings_and_errors():
    with pytest.warns(UserWarning, match="single character string"):
        assert stri_join_list([["a", "b"]], sep=["-", "+"]) == ["a-b"]
    with pytest.raises(ValueError, match="list of character vectors"):
        stri_join_list(None)
    with pytest.raises(ValueError, match="list of character vectors"):
        stri_join_list("ab")
    with pytest.raises(ValueError, match="argument `sep` should be a non-empty vector"):
        stri_join_list([["a"]], sep=[])
    with pytest.raises(ValueError, match="argument `collapse` should be a non-empty vector"):
        stri_join_list([["a", "b"]], collapse=[])


R_ORACLE = r"""
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
json_one <- function(s) {
  if (length(s) != 1) stop("json_one length")
  if (is.na(s)) return("null")
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_chr <- function(x) {
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(x, json_one, ""), collapse = ","), "]")
}
run <- function(expr) {
  tryCatch(
    json_chr(suppressWarnings(eval(expr))),
    error = function(e) paste0('{"error":', json_one(conditionMessage(e)), "}")
  )
}
cases <- alist(
  dup_known = stri_dup(c("a", NA), 2),
  dup_na_string = stri_dup("NA", 2),
  dup_seq = stri_dup("a", 1:5),
  dup_na4 = stri_dup(c("a", NA, "ba"), 4),
  dup_mixed = stri_dup(c("abc", "pqrst"), c(4, 2)),
  dup_zero = stri_dup("ab", 0),
  dup_neg = stri_dup("ab", -1),
  dup_times_na = stri_dup("ab", NA),
  dup_na_zero = stri_dup(NA, 0),
  dup_empty = stri_dup("", 3),
  dup_empty_neg = stri_dup("", -1),
  dup_empty_vec = stri_dup(character(0), 2),
  dup_times_empty = stri_dup("a", integer(0)),
  dup_null = stri_dup(NULL, 2),
  dup_times_null = stri_dup("a", NULL),
  dup_recycle = stri_dup(c("a", "b", "c"), c(1, 2)),
  dup_float = stri_dup("ab", 2.9),
  dup_neg_float = stri_dup("ab", -1.2),
  dup_small = stri_dup("ab", 0.9),
  dup_neg_small = stri_dup("ab", -0.9),
  dup_logical = stri_dup(c(TRUE, FALSE, NA), 2),
  dup_num = stri_dup(c(1, NA, 1.5), 2),
  dup_true = stri_dup("ab", TRUE),
  dup_false = stri_dup("ab", FALSE),
  dup_unicode = stri_dup("ą", 3),
  dup_char = stri_dup("a", "2"),
  dup_char_float = stri_dup("ab", "2.9"),
  dup_plus = stri_dup("a", "+3"),
  dup_space = stri_dup("a", " 2"),
  dup_hex = stri_dup("ab", "0x2"),
  dup_inf = stri_dup("a", Inf),
  dup_nan = stri_dup("a", NaN),
  dup_bad = stri_dup("a", "x"),
  dup_big_char = stri_dup("a", "2147483648"),
  dup_empty_char_times = stri_dup("ab", ""),
  dup_na_char_times = stri_dup("ab", "NA"),
  join_known = stri_join(1:3, c("a", "b", "c"), sep = "-"),
  join_na = stri_join(c("a", NA, "c"), c("x", "y", "z"), sep = "-"),
  join_na_string = stri_join(c("NA", "a"), "b"),
  join_empty = stri_join(c("a", "b"), character(0), "c"),
  join_ignore = stri_join(c("a", "b"), character(0), "c", ignore_null = TRUE),
  join_none = stri_join(),
  join_none_collapse = stri_join(collapse = ","),
  join_none_collapse_na = stri_join(collapse = NA),
  join_none_collapse_empty = stri_join(collapse = character(0)),
  join_ignore_all = stri_join(character(0), character(0), ignore_null = TRUE),
  join_ignore_collapse = stri_join(character(0), collapse = ",", ignore_null = TRUE),
  join_one = stri_join(c("a", NA, "b")),
  join_one_collapse = stri_join(c("a", NA, "b"), collapse = ","),
  join_collapse_na = stri_join(c("a", NA), c("x", "y"), collapse = "-"),
  join_sep_na = stri_join(c("a", "b"), c("x", "y"), sep = NA),
  join_sep_na_collapse = stri_join(c("a", "b"), c("x", "y"), sep = NA, collapse = ","),
  join_collapse_na_arg = stri_join(c("a", "b"), collapse = NA),
  join_recycle = stri_join(c("a", "b"), c("x", "y", "z"), sep = "-"),
  join_sep_long = stri_join(c("a", "b"), c("x", "y"), sep = c("-", "+")),
  join_empty_str = stri_join(c("a", ""), c("b", "c"), sep = "-"),
  join_logical = stri_join(c(TRUE, FALSE, NA), "x"),
  join_double = stri_join(c(0.0001, 100000, NA, NaN, Inf, -Inf), "z", sep = "|"),
  join_three = stri_join("a", "b", "c", sep = "-"),
  join_collapse_empty = stri_join(c("a", "b", "c"), collapse = ""),
  join_two_na_collapse = stri_join(c("a", NA), c("x", "y"), sep = "", collapse = "-"),
  join_one_empty_collapse = stri_join(character(0), collapse = ","),
  join_one_empty = stri_join(character(0)),
  join_int_na = stri_join(c(1L, NA_integer_, 3L), "x", sep = "-"),
  join_sep_num = stri_join("a", "b", sep = 1),
  join_collapse_false = stri_join(c("a", "b"), collapse = FALSE),
  join_null = stri_join(NULL, c("a", "b")),
  join_null_ignore = stri_join(NULL, c("a", "b"), ignore_null = TRUE),
  join_sep_ignored = stri_join(c("a", "b"), sep = "-"),
  join_sep_ignored_collapse = stri_join(c("a", "b"), sep = "XXX", collapse = ","),
  join_empty_collapse = stri_join(c("a", "b"), character(0), collapse = ","),
  join_empty_collapse_na = stri_join(c("a", "b"), character(0), collapse = NA),
  join_empty_sep_na = stri_join(c("a", "b"), character(0), sep = NA, collapse = ","),
  join_empty_vec_collapse_na = stri_join(character(0), collapse = NA),
  join_pair_collapse = stri_join(c("a", "b"), c("x", "y"), sep = "", collapse = "-"),
  join_pair_sep_collapse = stri_join(c("a", "b"), c("x", "y"), sep = "-", collapse = "|"),
  join_unicode = stri_join("ą", "ę", sep = "-"),
  join_list_scalar = stri_join(list("a", "b"), "x", sep = "-"),
  join_sep_na_string = stri_join("a", "b", sep = "NA"),
  join_ignore_char = stri_join(character(0), "a", ignore_null = "TRUE"),
  join_ignore_one = stri_join(character(0), "a", ignore_null = 1),
  flat_letters = stri_flatten(c("A", "B", "C"), collapse = ","),
  flat_empty = stri_flatten(character(0)),
  flat_empty_comma = stri_flatten(character(0), collapse = ","),
  flat_null = stri_flatten(NULL),
  flat_na = stri_flatten(c("a", NA, "b"), collapse = ","),
  flat_na_true = stri_flatten(c("a", NA, "b"), collapse = ",", na_empty = TRUE),
  flat_na_na = stri_flatten(c("a", NA, "b"), collapse = ",", na_empty = NA),
  flat_omit = stri_flatten(c("a", "", "b"), collapse = ",", omit_empty = TRUE),
  flat_both = stri_flatten(c(NA, "", "A", "", "B", NA, "C"), collapse = ",", na_empty = TRUE, omit_empty = TRUE),
  flat_na_keep_empty = stri_flatten(c(NA, "", "A", "", "B", NA, "C"), collapse = ",", na_empty = NA),
  flat_na_omit = stri_flatten(c(NA, "", "A", "", "B", NA, "C"), collapse = ",", na_empty = NA, omit_empty = TRUE),
  flat_na_false_omit = stri_flatten(c(NA, "", "A"), collapse = ",", na_empty = FALSE, omit_empty = TRUE),
  flat_empty_sep_na = stri_flatten(c("a", "", "b", NA), collapse = "", omit_empty = TRUE),
  flat_empty_sep_omit = stri_flatten(c("a", "", "b"), collapse = "", omit_empty = TRUE),
  flat_empty_sep_true = stri_flatten(c("a", NA, "b"), collapse = "", na_empty = TRUE),
  flat_empty_sep_drop = stri_flatten(c("a", NA, "", "b"), collapse = "", na_empty = NA, omit_empty = TRUE),
  flat_collapse_na = stri_flatten(c("a", "b"), collapse = NA),
  flat_long = stri_flatten(c("a", "b"), collapse = c(",", "+")),
  flat_single = stri_flatten("a", collapse = ","),
  flat_only_empty = stri_flatten(c("", ""), collapse = ",", omit_empty = TRUE),
  flat_only_na_omit = stri_flatten(c(NA, NA), collapse = ",", na_empty = TRUE, omit_empty = TRUE),
  flat_only_na_drop = stri_flatten(c(NA, NA), collapse = ",", na_empty = NA),
  flat_two_na_slots = stri_flatten(c(NA, NA), collapse = ",", na_empty = TRUE),
  flat_only_na = stri_flatten(NA, collapse = ","),
  flat_lead = stri_flatten(c("", "a", "", "b", ""), collapse = "|", omit_empty = TRUE),
  flat_slots = stri_flatten(c(NA, "a", NA, "b"), collapse = "|", na_empty = TRUE),
  flat_lead_na = stri_flatten(c(NA, "a"), collapse = "|", na_empty = TRUE),
  flat_string_na = stri_flatten(c("NA", "a"), collapse = ","),
  flat_num = stri_flatten(1:3, collapse = "-"),
  flat_all_omit = stri_flatten(c("", NA), collapse = ",", na_empty = TRUE, omit_empty = TRUE),
  flat_keep_empty = stri_flatten(c("", "a", ""), collapse = ",", na_empty = NA),
  flat_one_na_true = stri_flatten(NA, collapse = ",", na_empty = TRUE),
  flat_one_na_empty_sep = stri_flatten(NA, collapse = "", na_empty = TRUE),
  flat_empty_collapse_na = stri_flatten(character(0), collapse = NA),
  flat_yes = stri_flatten("a", na_empty = "yes"),
  flat_true_word = stri_flatten(c("a", NA), collapse = ",", na_empty = "TRUE"),
  flat_t_word = stri_flatten(c("a", NA), collapse = ",", na_empty = "T"),
  flat_na_empty_one = stri_flatten(c("a", NA), collapse = ",", na_empty = 1),
  flat_zero = stri_flatten(c("a", NA), collapse = ",", na_empty = 0),
  flat_omit_word = stri_flatten(c("a", ""), collapse = ",", omit_empty = "TRUE"),
  jlist = stri_join_list(list(c("a", "b"), c("c", NA), character(0), "d"), sep = "-"),
  jlist_collapse = stri_join_list(list(c("a", "b"), c("c", NA), character(0), "d"), sep = "-", collapse = "|"),
  jlist_empty = stri_join_list(list(), sep = ","),
  jlist_empty_collapse = stri_join_list(list(), collapse = ","),
  jlist_empty_sep = stri_join_list(list(), sep = character(0)),
  jlist_nulls = stri_join_list(list(character(0), NULL), sep = ","),
  jlist_sep_na = stri_join_list(list(c("a", "b"), c("c", "d")), sep = NA),
  jlist_sep_na_collapse = stri_join_list(list(c("a", "b")), sep = NA, collapse = ","),
  jlist_collapse_na = stri_join_list(list(c("a", "b"), "c"), collapse = NA),
  jlist_inner = stri_join_list(list(c("a", NA), "b"), sep = ",", collapse = "|"),
  jlist_empty_piece = stri_join_list(list(c("a", "")), sep = "-"),
  jlist_both_empty = stri_join_list(list(c("a", "b"), "c"), sep = "", collapse = ""),
  jlist_num = stri_join_list(list(1:3, c(4, 5)), sep = ","),
  jlist_scalars = stri_join_list(list("a", "b"), sep = ""),
  jlist_scalars_sep = stri_join_list(list("a", "b"), sep = "-"),
  jlist_one = stri_c_list(list(c("a", "b")), sep = "-"),
  jlist_paste = stri_paste_list(list(c("a", "b"), "c"), collapse = "|"),
  jlist_na_nosep = stri_join_list(list(c("a", NA, "b")), sep = ""),
  jlist_empty_nosep = stri_join_list(list(c("a", "", "b")), sep = ""),
  jlist_long_sep = stri_join_list(list(c("a", "b")), sep = c("-", "+")),
  err_sep = stri_join("a", "b", sep = character(0)),
  err_collapse = stri_join("a", "b", collapse = character(0)),
  err_ignore = stri_join("a", ignore_null = NA),
  err_omit = stri_flatten("a", omit_empty = NA),
  err_x_null = stri_join_list(NULL),
  err_x_chr = stri_join_list(c("a", "b")),
  err_list_sep = stri_join_list(list("a"), sep = character(0)),
  err_list_collapse = stri_join_list(list(c("a", "b")), collapse = character(0)),
  err_sep_null = stri_join("a", "b", sep = NULL),
  err_na_empty = stri_flatten("a", na_empty = logical(0)),
  c_alias = stri_c(1:3, c("a", "b", "c"), sep = "-"),
  paste_alias = stri_paste(c("a", NA), c("x", "y"), sep = "-")
)
cat("{\n")
nms <- names(cases)
for (i in seq_along(cases)) {
  comma <- if (i < length(cases)) "," else ""
  cat(sprintf('"%s":%s%s\n', nms[[i]], run(cases[[i]]), comma))
}
cat("}\n")
"""


def _python_oracle():
    return {
        "dup_known": stri_dup(["a", NA], 2),
        "dup_na_string": stri_dup("NA", 2),
        "dup_seq": stri_dup("a", range(1, 6)),
        "dup_na4": stri_dup(["a", NA, "ba"], 4),
        "dup_mixed": stri_dup(["abc", "pqrst"], [4, 2]),
        "dup_zero": stri_dup("ab", 0),
        "dup_neg": stri_dup("ab", -1),
        "dup_times_na": stri_dup("ab", NA),
        "dup_na_zero": stri_dup(NA, 0),
        "dup_empty": stri_dup("", 3),
        "dup_empty_neg": stri_dup("", -1),
        "dup_empty_vec": stri_dup([], 2),
        "dup_times_empty": stri_dup("a", []),
        "dup_null": stri_dup(None, 2),
        "dup_times_null": stri_dup("a", None),
        "dup_recycle": stri_dup(["a", "b", "c"], [1, 2]),
        "dup_float": stri_dup("ab", 2.9),
        "dup_neg_float": stri_dup("ab", -1.2),
        "dup_small": stri_dup("ab", 0.9),
        "dup_neg_small": stri_dup("ab", -0.9),
        "dup_logical": stri_dup([True, False, NA], 2),
        "dup_num": stri_dup([1, NA, 1.5], 2),
        "dup_true": stri_dup("ab", True),
        "dup_false": stri_dup("ab", False),
        "dup_unicode": stri_dup("ą", 3),
        "dup_char": stri_dup("a", "2"),
        "dup_char_float": stri_dup("ab", "2.9"),
        "dup_plus": stri_dup("a", "+3"),
        "dup_space": stri_dup("a", " 2"),
        "dup_hex": stri_dup("ab", "0x2"),
        "dup_inf": stri_dup("a", math.inf),
        "dup_nan": stri_dup("a", math.nan),
        "dup_bad": stri_dup("a", "x"),
        "dup_big_char": stri_dup("a", "2147483648"),
        "dup_empty_char_times": stri_dup("ab", ""),
        "dup_na_char_times": stri_dup("ab", "NA"),
        "join_known": stri_join([1, 2, 3], ["a", "b", "c"], sep="-"),
        "join_na": stri_join(["a", NA, "c"], ["x", "y", "z"], sep="-"),
        "join_na_string": stri_join(["NA", "a"], "b"),
        "join_empty": stri_join(["a", "b"], [], "c"),
        "join_ignore": stri_join(["a", "b"], [], "c", ignore_null=True),
        "join_none": stri_join(),
        "join_none_collapse": stri_join(collapse=","),
        "join_none_collapse_na": stri_join(collapse=NA),
        "join_none_collapse_empty": stri_join(collapse=[]),
        "join_ignore_all": stri_join([], [], ignore_null=True),
        "join_ignore_collapse": stri_join([], collapse=",", ignore_null=True),
        "join_one": stri_join(["a", NA, "b"]),
        "join_one_collapse": stri_join(["a", NA, "b"], collapse=","),
        "join_collapse_na": stri_join(["a", NA], ["x", "y"], collapse="-"),
        "join_sep_na": stri_join(["a", "b"], ["x", "y"], sep=NA),
        "join_sep_na_collapse": stri_join(["a", "b"], ["x", "y"], sep=NA, collapse=","),
        "join_collapse_na_arg": stri_join(["a", "b"], collapse=NA),
        "join_recycle": stri_join(["a", "b"], ["x", "y", "z"], sep="-"),
        "join_sep_long": stri_join(["a", "b"], ["x", "y"], sep=["-", "+"]),
        "join_empty_str": stri_join(["a", ""], ["b", "c"], sep="-"),
        "join_logical": stri_join([True, False, NA], "x"),
        "join_double": stri_join(
            [0.0001, 100000.0, NA, math.nan, math.inf, -math.inf], "z", sep="|"
        ),
        "join_three": stri_join("a", "b", "c", sep="-"),
        "join_collapse_empty": stri_join(["a", "b", "c"], collapse=""),
        "join_two_na_collapse": stri_join(["a", NA], ["x", "y"], sep="", collapse="-"),
        "join_one_empty_collapse": stri_join([], collapse=","),
        "join_one_empty": stri_join([]),
        "join_int_na": stri_join([1, NA, 3], "x", sep="-"),
        "join_sep_num": stri_join("a", "b", sep=1),
        "join_collapse_false": stri_join(["a", "b"], collapse=False),
        "join_null": stri_join(None, ["a", "b"]),
        "join_null_ignore": stri_join(None, ["a", "b"], ignore_null=True),
        "join_sep_ignored": stri_join(["a", "b"], sep="-"),
        "join_sep_ignored_collapse": stri_join(["a", "b"], sep="XXX", collapse=","),
        "join_empty_collapse": stri_join(["a", "b"], [], collapse=","),
        "join_empty_collapse_na": stri_join(["a", "b"], [], collapse=NA),
        "join_empty_sep_na": stri_join(["a", "b"], [], sep=NA, collapse=","),
        "join_empty_vec_collapse_na": stri_join([], collapse=NA),
        "join_pair_collapse": stri_join(["a", "b"], ["x", "y"], sep="", collapse="-"),
        "join_pair_sep_collapse": stri_join(["a", "b"], ["x", "y"], sep="-", collapse="|"),
        "join_unicode": stri_join("ą", "ę", sep="-"),
        "join_list_scalar": stri_join(["a", "b"], "x", sep="-"),
        "join_sep_na_string": stri_join("a", "b", sep="NA"),
        "join_ignore_char": stri_join([], "a", ignore_null="TRUE"),
        "join_ignore_one": stri_join([], "a", ignore_null=1),
        "flat_letters": stri_flatten(["A", "B", "C"], collapse=","),
        "flat_empty": stri_flatten([]),
        "flat_empty_comma": stri_flatten([], collapse=","),
        "flat_null": stri_flatten(None),
        "flat_na": stri_flatten(["a", NA, "b"], collapse=","),
        "flat_na_true": stri_flatten(["a", NA, "b"], collapse=",", na_empty=True),
        "flat_na_na": stri_flatten(["a", NA, "b"], collapse=",", na_empty=NA),
        "flat_omit": stri_flatten(["a", "", "b"], collapse=",", omit_empty=True),
        "flat_both": stri_flatten(
            [NA, "", "A", "", "B", NA, "C"], collapse=",", na_empty=True, omit_empty=True
        ),
        "flat_na_keep_empty": stri_flatten(
            [NA, "", "A", "", "B", NA, "C"], collapse=",", na_empty=NA
        ),
        "flat_na_omit": stri_flatten(
            [NA, "", "A", "", "B", NA, "C"], collapse=",", na_empty=NA, omit_empty=True
        ),
        "flat_na_false_omit": stri_flatten(
            [NA, "", "A"], collapse=",", na_empty=False, omit_empty=True
        ),
        "flat_empty_sep_na": stri_flatten(["a", "", "b", NA], collapse="", omit_empty=True),
        "flat_empty_sep_omit": stri_flatten(["a", "", "b"], collapse="", omit_empty=True),
        "flat_empty_sep_true": stri_flatten(["a", NA, "b"], collapse="", na_empty=True),
        "flat_empty_sep_drop": stri_flatten(
            ["a", NA, "", "b"], collapse="", na_empty=NA, omit_empty=True
        ),
        "flat_collapse_na": stri_flatten(["a", "b"], collapse=NA),
        "flat_long": stri_flatten(["a", "b"], collapse=[",", "+"]),
        "flat_single": stri_flatten("a", collapse=","),
        "flat_only_empty": stri_flatten(["", ""], collapse=",", omit_empty=True),
        "flat_only_na_omit": stri_flatten([NA, NA], collapse=",", na_empty=True, omit_empty=True),
        "flat_only_na_drop": stri_flatten([NA, NA], collapse=",", na_empty=NA),
        "flat_two_na_slots": stri_flatten([NA, NA], collapse=",", na_empty=True),
        "flat_only_na": stri_flatten(NA, collapse=","),
        "flat_lead": stri_flatten(["", "a", "", "b", ""], collapse="|", omit_empty=True),
        "flat_slots": stri_flatten([NA, "a", NA, "b"], collapse="|", na_empty=True),
        "flat_lead_na": stri_flatten([NA, "a"], collapse="|", na_empty=True),
        "flat_string_na": stri_flatten(["NA", "a"], collapse=","),
        "flat_num": stri_flatten([1, 2, 3], collapse="-"),
        "flat_all_omit": stri_flatten(["", NA], collapse=",", na_empty=True, omit_empty=True),
        "flat_keep_empty": stri_flatten(["", "a", ""], collapse=",", na_empty=NA),
        "flat_one_na_true": stri_flatten(NA, collapse=",", na_empty=True),
        "flat_one_na_empty_sep": stri_flatten(NA, collapse="", na_empty=True),
        "flat_empty_collapse_na": stri_flatten([], collapse=NA),
        "flat_yes": stri_flatten("a", na_empty="yes"),
        "flat_true_word": stri_flatten(["a", NA], collapse=",", na_empty="TRUE"),
        "flat_t_word": stri_flatten(["a", NA], collapse=",", na_empty="T"),
        "flat_na_empty_one": stri_flatten(["a", NA], collapse=",", na_empty=1),
        "flat_zero": stri_flatten(["a", NA], collapse=",", na_empty=0),
        "flat_omit_word": stri_flatten(["a", ""], collapse=",", omit_empty="TRUE"),
        "jlist": stri_join_list([["a", "b"], ["c", NA], [], "d"], sep="-"),
        "jlist_collapse": stri_join_list(
            [["a", "b"], ["c", NA], [], "d"], sep="-", collapse="|"
        ),
        "jlist_empty": stri_join_list([], sep=","),
        "jlist_empty_collapse": stri_join_list([], collapse=","),
        "jlist_empty_sep": stri_join_list([], sep=[]),
        "jlist_nulls": stri_join_list([[], None], sep=","),
        "jlist_sep_na": stri_join_list([["a", "b"], ["c", "d"]], sep=NA),
        "jlist_sep_na_collapse": stri_join_list([["a", "b"]], sep=NA, collapse=","),
        "jlist_collapse_na": stri_join_list([["a", "b"], "c"], collapse=NA),
        "jlist_inner": stri_join_list([["a", NA], "b"], sep=",", collapse="|"),
        "jlist_empty_piece": stri_join_list([["a", ""]], sep="-"),
        "jlist_both_empty": stri_join_list([["a", "b"], "c"], sep="", collapse=""),
        "jlist_num": stri_join_list([[1, 2, 3], [4, 5]], sep=","),
        "jlist_scalars": stri_join_list(["a", "b"], sep=""),
        "jlist_scalars_sep": stri_join_list(["a", "b"], sep="-"),
        "jlist_one": stri_c_list([["a", "b"]], sep="-"),
        "jlist_paste": stri_paste_list([["a", "b"], "c"], collapse="|"),
        "jlist_na_nosep": stri_join_list([["a", NA, "b"]], sep=""),
        "jlist_empty_nosep": stri_join_list([["a", "", "b"]], sep=""),
        "jlist_long_sep": stri_join_list([["a", "b"]], sep=["-", "+"]),
        "err_sep": "argument `sep` should be a non-empty vector",
        "err_collapse": "argument `collapse` should be a non-empty vector",
        "err_ignore": "missing values in argument `ignore_null` is not supported",
        "err_omit": "missing values in argument `omit_empty` is not supported",
        "err_x_null": "argument `x` should be a list of character vectors (or an object coercible to)",
        "err_x_chr": "argument `x` should be a list of character vectors (or an object coercible to)",
        "err_list_sep": "argument `sep` should be a non-empty vector",
        "err_list_collapse": "argument `collapse` should be a non-empty vector",
        "err_sep_null": "argument `sep` should be a non-empty vector",
        "err_na_empty": "argument `na_empty` should be a non-empty vector",
        "c_alias": stri_c([1, 2, 3], ["a", "b", "c"], sep="-"),
        "paste_alias": stri_paste(["a", NA], ["x", "y"], sep="-"),
    }


def _shown(value):
    if isinstance(value, str):
        return value
    return [None if item is NA else item for item in value]


def test_values_match_r():
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False, encoding="utf-8") as handle:
        handle.write(R_ORACLE)
        script_path = handle.name
    try:
        completed = subprocess.run(
            ["Rscript", script_path],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(script_path)
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        expected = _python_oracle()
    assert observed.keys() == expected.keys()
    mismatches = []
    for name, python_value in expected.items():
        r_value = observed[name]
        if isinstance(r_value, dict) and "error" in r_value:
            if r_value["error"] != python_value:
                mismatches.append((name, r_value, python_value))
            continue
        if _shown(python_value) != r_value:
            mismatches.append((name, r_value, _shown(python_value)))
    assert mismatches == []
