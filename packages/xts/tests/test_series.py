"""The xts constructor and the functions that use it, against the R 0.14.3 results."""

from datetime import datetime, timedelta, timezone

import pytest

from xts import (
    CLASS,
    adj_time,
    apply_daily,
    as_environment,
    as_xts,
    ax_ticks_by_time,
    c_xts,
    cbind_xts,
    convertIndex,
    diff_xts,
    dimnames_set,
    dimnames_xts,
    dot_xts,
    endpoints,
    first,
    indexDate,
    index_get,
    index_set,
    indexday,
    indexhour,
    indexisdst,
    indexmday,
    indexmin,
    indexmon,
    indexsec,
    indexwday,
    indexweek,
    indexyday,
    indexyear,
    is_time_based,
    is_time_unique,
    is_xts,
    lag_xts,
    last,
    make_index_unique,
    merge_xts,
    parse_iso8601,
    period_max,
    period_min,
    period_prod,
    period_sum,
    periodicity,
    plot_xts,
    rbind_xts,
    shift_time,
    split_xts,
    subset_xts,
    subset_xts_rows,
    tclass,
    tformat_set,
    time_based,
    time_based_range,
    time_based_seq,
    to_daily,
    to_hourly,
    to_minutes,
    to_minutes3,
    to_weekly,
    tzone,
    xcoredata,
    xts,
    xtsAttributes,
    xtsAttributes_set,
    xtsible,
    add_event_lines,
    add_legend,
    add_panel,
    add_polygon,
    add_series,
)
from xts.ordered import XtsError


def _stamp(day=1, hour=0):
    return datetime(2020, 1, day, hour, tzinfo=timezone.utc)


def _series(n=5, step=86400):
    start = _stamp()
    order = [start + timedelta(seconds=step * i) for i in range(n)]
    return xts(list(range(1, n + 1)), order)


def _flat(series):
    parts = []
    for value in series.flat():
        parts.append("NA" if value is None else format(float(value), ".10g"))
    return "|".join(parts)


def test_constructor_and_index_parts():
    series = _series()
    assert _flat(series) == "1|2|3|4|5"
    assert "|".join(format(value, ".0f") for value in index_get(series)) == (
        "1577836800|1577923200|1578009600|1578096000|1578182400"
    )
    assert tzone(series) == "UTC"
    assert tclass(series) == ["POSIXct", "POSIXt"]
    assert is_xts(series) is True
    assert is_xts([1, 2, 3]) is False
    built = dot_xts([1, 2, 3], [10, 20, 30], tzone="UTC")
    assert _flat(built) == "1|2|3"
    assert tclass(built) == ["POSIXct", "POSIXt"]
    matrix = as_xts([[1, 2, 3], [4, 5, 6]], [_stamp(1), _stamp(2), _stamp(3)])
    assert _flat(matrix) == "1|2|3|4|5|6"
    assert indexsec(series) == [0, 0, 0, 0, 0]
    assert indexmin(series) == [0, 0, 0, 0, 0]
    assert indexhour(series) == [0, 0, 0, 0, 0]
    assert indexmday(series) == [1, 2, 3, 4, 5]
    assert indexmon(series) == [0, 0, 0, 0, 0]
    assert indexyear(series) == [120, 120, 120, 120, 120]
    assert indexwday(series) == [3, 4, 5, 6, 0]
    assert indexyday(series) == [0, 1, 2, 3, 4]
    assert indexisdst(series) == [0, 0, 0, 0, 0]
    assert indexDate(series) == [18262, 18263, 18264, 18265, 18266]
    assert indexday(series) == indexDate(series)
    assert indexweek(series) == [2609, 2609, 2609, 2609, 2609]


def test_time_strings_lag_and_periods():
    parsed = parse_iso8601("2000-05/2001-02")
    assert format(parsed["first.time"], ".0f") == "957132000"
    assert format(parsed["last.time"], ".0f") == "983401200"
    assert is_time_based(datetime(2020, 1, 1).date()) is True
    assert time_based(1) is False
    assert [format(value, ".0f") for value in time_based_range("2000-05/2001-02")] == ["957132000", "983401200"]
    assert time_based_seq("20080101/20080103") == [13879, 13880, 13881]
    series = _series()
    assert _flat(lag_xts(series)) == "NA|1|2|3|4"
    assert _flat(diff_xts(series)) == "NA|1|1|1|1"
    ends = endpoints(series, "days")
    assert _flat(period_sum(series, ends)) == "1|2|3|4|5"
    assert _flat(period_prod(series, ends)) == "1|2|3|4|5"
    assert _flat(period_min(series, ends)) == "1|2|3|4|5"
    assert _flat(period_max(series, ends)) == "1|2|3|4|5"
    assert periodicity(series)["scale"] == "daily"
    assert periodicity(series)["frequency"] == 86400
    weekly = xts(list(range(1, 15)), [_stamp(1) + timedelta(days=i) for i in range(14)])
    assert _flat(to_weekly(weekly)) == "1|6|13|5|12|14|1|6|13|5|12|14"
    assert "|".join(format(value, ".0f") for value in weekly.index[:1])
    got = to_weekly(weekly)
    assert "|".join(format(value, ".0f") for value in got.index) == "1578182400|1578787200|1578960000"


def test_join_unique_subset_and_plot():
    series = _series()
    other = xts([10, 20, 30], [_stamp(1), _stamp(3), _stamp(5)])
    assert _flat(merge_xts(series, other)) == "1|2|3|4|5|10|NA|20|NA|30"
    assert _flat(cbind_xts(series, other)) == "1|2|3|4|5|10|NA|20|NA|30"
    assert _flat(c_xts(series, series)) == "1|1|2|2|3|3|4|4|5|5"
    bumped = xts(list(range(11, 16)), [_stamp(day) for day in range(1, 6)])
    assert _flat(rbind_xts(series, bumped)) == "1|11|2|12|3|13|4|14|5|15"
    unique = make_index_unique(dot_xts([1, 2, 3, 4], [1, 1, 1, 2], tzone="UTC"))
    assert "|".join(format(value, ".6f") for value in unique.index) == "1.000000|1.000001|1.000002|2.000000"
    assert is_time_unique(unique) is True
    shifted = shift_time(series, 60)
    assert "|".join(format(value, ".0f") for value in shifted.index) == (
        "1577836860|1577923260|1578009660|1578096060|1578182460"
    )
    assert _flat(subset_xts(series, "2020-01-03")) == "3"
    assert _flat(subset_xts_rows(series, [1, 2])) == "1|2"
    assert _flat(first(series, "2 days")) == "1|2"
    assert _flat(last(series, "2 days")) == "4|5"
    assert _flat(apply_daily(series, sum)) == "1|2|3|4|5"
    assert ax_ticks_by_time(series, "days") == [1, 2, 3, 4, 5, 5]
    pieces = split_xts(series, "months")
    assert len(pieces) == 1 and _flat(pieces[0]) == "1|2|3|4|5"
    hourly = xts([1, 2, 3], [_stamp(1, hour) for hour in range(3)])
    assert _flat(to_daily(hourly)) == "1|3|1|3"
    assert _flat(to_minutes(hourly)) == "1|2|3|1|2|3|1|2|3|1|2|3"
    assert _flat(to_hourly(hourly)) == "1|2|3|1|2|3|1|2|3|1|2|3"
    assert _flat(to_minutes3(hourly)) == "1|2|3|1|2|3|1|2|3|1|2|3"
    named = dimnames_set(series, [None, "a"])
    assert dimnames_xts(named)[1] == ["a"]
    assert as_environment(named)["a"] == [1, 2, 3, 4, 5]
    assert CLASS(series) is None
    assert xtsAttributes(series) is None
    tagged = xtsAttributes_set(series, {"descr": "mine"})
    assert xtsAttributes(tagged)["descr"] == "mine"
    assert "descr" in xcoredata(tagged)
    moved = index_set(series, [value + 10 for value in series.index])
    assert index_get(moved)[0] == pytest.approx(1577836810)
    formatted = tformat_set(series, "%Y")
    assert formatted.tformat == "%Y"
    converted = convertIndex(series, "Date")
    assert converted.tclass == ["Date"]
    assert xtsible(series) is True
    assert xtsible(1) is False
    with pytest.raises(XtsError, match="month"):
        adj_time(series.index[0], sec=0)
    assert plot_xts(series) == "1577836800|1578182400|1|5"
    wider = xts([2, 4, 6, 8, 10], [_stamp(day) for day in range(1, 6)])
    assert add_series(wider) == "2|10"
    plot_xts(series)
    assert add_panel(lambda item: item) == "2"
    plot_xts(series)
    assert add_legend("topleft", legend_names="a") == "5"
    plot_xts(series)
    assert add_event_lines(xts([1], [_stamp(3)])) == "5"
    plot_xts(series)
    low = xts([0, 1, 2, 3, 4], [_stamp(day) for day in range(1, 6)])
    high = xts([2, 3, 4, 5, 6], [_stamp(day) for day in range(1, 6)])
    assert add_polygon(cbind_xts(low, high)) == "0|6"
