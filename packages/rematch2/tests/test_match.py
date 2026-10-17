import pytest

from rematch2 import (
    bind_re_match,
    bind_re_match_,
    dollar_rematch_allrecords,
    dollar_rematch_records,
    re_exec,
    re_exec_all,
    re_match,
    re_match_all,
)
from tibble import tibble

DATES = [
    "2016-04-20",
    "1977-08-08",
    "not a date",
    "2016",
    "76-03-02",
    "2012-06-30",
    "2015-01-21 19:58",
]
ISODATE = "(?<year>[0-9]{4})-(?<month>[0-1][0-9])-(?<day>[0-3][0-9])"
NAME = "(?<first>[[:upper:]][[:lower:]]+) (?<last>[[:upper:]][[:lower:]]+)"
NOTABLES = ["  Ben Franklin and Jefferson Davis", "\tMillard Fillmore"]


def test_re_match_named_dates():
    frame = re_match(DATES, ISODATE)
    assert frame.names == ["year", "month", "day", ".text", ".match"]
    assert frame["year"] == ["2016", "1977", None, None, None, "2012", "2015"]
    assert frame["month"] == ["04", "08", None, None, None, "06", "01"]
    assert frame["day"] == ["20", "08", None, None, None, "30", "21"]
    assert frame[".match"][0] == "2016-04-20"
    assert frame[".match"][2] is None
    assert frame[".text"] == DATES


def test_re_match_perl_false_drops_groups():
    frame = re_match(DATES, "([0-9]{4})", perl=False)
    assert frame.names == [".text", ".match"]
    assert frame[".match"] == ["2016", "1977", None, "2016", None, "2012", "2015"]


def test_re_match_unmatched_group_is_empty_at_zero():
    frame = re_match("b", "(a)|(b)")
    assert frame.names == ["", "", ".text", ".match"]
    assert frame.columns[0] == [""]
    assert frame.columns[1] == ["b"]


def test_re_match_na_text():
    frame = re_match(["a", None], "(a)")
    assert frame[".match"] == ["a", None]
    assert frame[".text"][1] is None


def test_re_match_empty():
    frame = re_match([], ISODATE)
    assert frame.nrow == 0
    assert frame.names == ["year", "month", "day", ".text", ".match"]


def test_posix_class_is_ascii():
    frame = re_match("Émile Zola", NAME)
    assert frame["first"] == [None]
    notables = re_match(NOTABLES, NAME)
    assert notables["first"] == ["Ben", "Millard"]
    assert notables["last"] == ["Franklin", "Fillmore"]


def test_re_match_all_notables():
    frame = re_match_all(NOTABLES, NAME)
    assert frame["first"] == [["Ben", "Jefferson"], ["Millard"]]
    assert frame["last"] == [["Franklin", "Davis"], ["Fillmore"]]
    assert frame[".match"][0] == ["Ben Franklin", "Jefferson Davis"]
    assert frame[".text"] == NOTABLES


def test_re_match_all_unmatched_group_and_miss():
    frame = re_match_all(["b", "a", "c"], "(a)|(b)")
    assert frame.columns[0] == [[""], ["a"], []]
    assert frame.columns[1] == [["b"], [""], []]
    assert frame[".match"] == [["b"], ["a"], []]


def test_re_match_all_empty():
    frame = re_match_all([], NAME)
    assert frame.nrow == 0
    assert frame.names == ["first", "last", ".text", ".match"]


def test_re_match_all_rejects_na():
    with pytest.raises(ValueError):
        re_match_all(["aa", None], "a")


def test_re_exec_positions():
    frame = re_exec(NOTABLES, NAME)
    assert frame["first"].match == ["Ben", "Millard"]
    assert frame["first"].start == [3, 2]
    assert frame["first"].end == [5, 8]
    assert dollar_rematch_records(frame["first"], "match") == ["Ben", "Millard"]
    missed = re_exec("b", "(?<one>a)|(?<two>b)")
    assert missed["one"].match == [""]
    assert missed["one"].start == [0]
    assert missed["one"].end == [-1]
    assert missed["two"].match == ["b"]
    assert missed["two"].start == [1]


def test_re_exec_no_match_is_na():
    frame = re_exec("none", "(?<first>[[:upper:]][[:lower:]]+)")
    assert frame["first"].match == [None]
    assert frame["first"].start == [None]
    assert frame["first"].end == [None]


def test_re_exec_empty():
    frame = re_exec([], "(?<a>x)")
    assert frame.nrow == 0
    assert frame.names == ["a", ".text", ".match"]
    assert frame["a"].match == []


def test_re_exec_all_positions():
    frame = re_exec_all(NOTABLES, NAME)
    assert frame["first"].match == [["Ben", "Jefferson"], ["Millard"]]
    assert dollar_rematch_allrecords(frame["first"], "match")[0] == ["Ben", "Jefferson"]
    both = re_exec_all("ab", "(?<one>a)|(?<two>b)")
    assert both["one"].match == [["a", ""]]
    assert both["one"].start == [[1, 0]]
    assert both["one"].end == [[1, -1]]
    assert both["two"].start == [[0, 2]]
    assert both["two"].match == [["", "b"]]


def test_re_exec_all_empty_and_miss():
    empty = re_exec_all([], "(?<a>x)")
    assert empty.nrow == 0
    missed = re_exec_all("c", NAME)
    assert missed["first"].match == [[]]
    assert missed[".match"].start == [[]]


def test_dollar_rejects_other_names():
    frame = re_exec("Ben", "(?<first>[[:upper:]][[:lower:]]+)")
    with pytest.raises(ValueError):
        dollar_rematch_records(frame["first"], "other")


def test_bind_re_match():
    cars = tibble(rowname=["Mazda RX4", "Datsun 710"], mpg=[21.0, 22.8])
    bound = bind_re_match(cars, "rowname", r"^(?<make>\w+) ?(?<model>.+)?$")
    assert bound.names == ["rowname", "mpg", "make", "model"]
    assert bound["make"] == ["Mazda", "Datsun"]
    assert bound["model"] == ["RX4", "710"]
    kept = bind_re_match_(
        cars, "rowname", r"^(?<make>\w+) ?(?<model>.+)?$", keep_match=True
    )
    assert kept.names[-1] == ".match"
    assert kept[".match"] == ["Mazda RX4", "Datsun 710"]


def test_bind_missing_column():
    cars = tibble(rowname=["Mazda RX4"])
    with pytest.raises(ValueError, match="not present"):
        bind_re_match(cars, "missing", "x")
