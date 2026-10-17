"""xts 0.14.3 time helpers against R."""

from datetime import datetime, timezone

import pytest

from xts import (
    align_time,
    endpoints,
    first,
    firstof,
    isOrdered,
    last,
    lastof,
    ndays,
    nhours,
    nminutes,
    nmonths,
    nquarters,
    nseconds,
    nweeks,
    nyears,
)
from xts.ordered import XtsError


def _daily():
    start = datetime(2020, 1, 15, tzinfo=timezone.utc).timestamp()
    return [start + index * 86400 for index in range(41)]


def test_is_ordered_examples():
    assert isOrdered(range(1, 11)) is True
    assert isOrdered(range(1, 11), increasing=False) is False
    assert isOrdered([1, *range(1, 11)]) is False
    assert isOrdered([1, *range(1, 11)], strictly=False) is True
    assert isOrdered(range(10, 0, -1), increasing=False) is True
    assert isOrdered([]) is True
    with pytest.raises(XtsError, match="character"):
        isOrdered(["a"])


def test_first_and_last():
    values = list(range(1, 11))
    assert first(values, 3) == [1, 2, 3]
    assert last(values, 3) == [8, 9, 10]
    assert first(values, -2) == [3, 4, 5, 6, 7, 8, 9, 10]
    assert last(values, -2) == [1, 2, 3, 4, 5, 6, 7, 8]
    rows = [[1, 5, 9], [2, 6, 10], [3, 7, 11], [4, 8, 12]]
    assert first(rows, 2) == [[1, 5, 9], [2, 6, 10]]


def test_clock_and_endpoints():
    assert firstof(2000) == pytest.approx(946681200, abs=1e-8)
    assert lastof(2007, 10) == pytest.approx(1193871599.99999, abs=1e-8)
    base = datetime(2020, 1, 1, 0, 0, 10, tzinfo=timezone.utc).timestamp()
    assert align_time([base + offset for offset in range(6)], 10) == [1577836820.0] * 6
    index = _daily()
    assert endpoints(index, "months") == [0, 17, 41]
    assert endpoints(index, "weeks") == [0, 5, 12, 19, 26, 33, 40, 41]
    assert ndays(index) == 41
    assert nweeks(index) == 7
    assert nmonths(index) == 2
    assert nquarters(index) == 1
    assert nyears(index) == 1
    assert nhours(index) == nminutes(index) == nseconds(index) == 41
