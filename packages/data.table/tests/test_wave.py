"""Checks for the first data.table wave."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datatable import (
    DataTable,
    as_idate,
    as_itime,
    between,
    between_op,
    chin,
    chmatch,
    cj,
    copy,
    fcoalesce,
    fifelse,
    first,
    flike,
    frev,
    frollmedian,
    frollsum,
    hour,
    ilike,
    isoyear,
    last,
    like,
    like_op,
    nafill,
    notin,
    plike,
    rleid,
    rleidv,
    rowid,
    shift,
    transpose,
    uniqueN,
    yday,
    year,
)
from datatable._util import DataTableError
from datatable.like import Factor


class _Xts(list):
    r_class = "xts"


def test_between_matches_the_closed_integer_case():
    assert between([1, 2, 3, 4, 5], 2, 4) == [False, True, True, True, False]
    assert between_op([1, 2, 3, 4], [2, 3]) == [False, True, True, False]
    assert between([1, None, 3], [None, 1, 2], [2, None, 4]) == [True, None, True]


def test_like_and_membership():
    assert like(["abc", "ABC", "xyz"], "ab") == [True, False, False]
    assert like_op(["abc", "ABC", "xyz"], "ab") == like(["abc", "ABC", "xyz"], "ab")
    assert ilike(["abc", "ABC"], "ab") == [True, True]
    assert flike(["a.b", "axb"], "a.b") == [True, False]
    assert plike(["abc", "a"], "^a") == [True, True]
    assert like(Factor(["ab", "cd", "ab"]), "a") == [True, False, True]
    assert notin([1, None], [1]) == [False, True]
    assert chin(["a", "b"], ["b", "c"]) == [False, True]
    assert chmatch(["b", "a", "z"], ["a", "b", "a"]) == [2, 1, None]


def test_ends_runs_and_fills():
    assert first([1, 2, 3, 4, 5]) == 1
    assert last([1, 2, 3, 4, 5]) == 5
    assert rleid(["a", "a", "b", "b", "a"]) == [1, 1, 2, 2, 3]
    assert rleidv([[1, 1, 2], ["a", "b", "b"]]) == [1, 2, 3]
    assert uniqueN([1, 1, None, 2, None]) == 3
    assert fcoalesce([None, 1, None], [2, None, 3]) == [2, 1, 3]
    assert fifelse([True, False, None], [1, 2, 3], [4, 5, 6]) == [1, 5, None]
    assert shift([1, 2, 3, 4, 5], [1, -1], fill=0) == [[0, 1, 2, 3, 4], [2, 3, 4, 5, 0]]
    assert nafill([1, None, None, 4], "locf") == [1, 1, 1, 4]
    assert frev([1, 2, 3, 4]) == [4, 3, 2, 1]
    assert copy([1, 2, 3]) == [1, 2, 3]


def test_idate_calendar():
    dates = ["2020-01-15", "2020-02-29", "1970-01-01", "1969-12-31", None]
    assert as_idate(dates) == [18276, 18321, 0, -1, None]
    assert year(dates) == [2020, 2020, 1970, 1969, None]
    assert yday(dates)[1] == 60
    assert isoyear(dates) == [2020, 2020, 1970, 1970, None]
    assert list(as_itime(["12:34:56", "01:02", None])) == [45296, 3720, None]
    assert hour(as_itime("12:34:56")) == [12]


def test_rolling_transpose_and_join():
    assert frollsum(list(range(1, 7)), 3) == [None, None, 6.0, 9.0, 12.0, 15.0]
    assert frollsum(list(range(1, 7)), 3, align="left") == [6.0, 9.0, 12.0, 15.0, None, None]
    assert frollsum([1, None, 3, 4], 2, na_rm=True) == [None, 1.0, 3.0, 7.0]
    assert frollmedian(list(range(1, 7)), 4) == [None, None, None, 2.5, 3.5, 4.5]
    assert transpose([[1, 2, 3], [4, 5]]) == [[1, 4], [2, 5], [3, None]]
    assert cj(["b", "a"], [2, 1]).columns == [["a", "a", "b", "b"], [1, 2, 1, 2]]
    assert rowid(["a", "b", "a", "a", "b"]) == [1, 1, 2, 3, 2]


def test_xts_stops():
    try:
        first(_Xts([1, 2, 3]))
    except DataTableError as exc:
        assert "xts" in str(exc)
    else:
        raise AssertionError("expected the xts stop")
