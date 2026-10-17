"""Checks that follow the lubridate examples, including the POSIXlt leap quirk."""

import numpy as np

from lubridate import (
    as_period, interval, mplus, period, time_length, ymd, ymd_hms, years,
)


def _slots(value):
    return np.asarray(value.slots(), dtype=float).reshape(-1)


def test_interval_period_uses_posixlt_year():
    documented = as_period(interval(ymd("1985-01-31"), ymd("1986-03-28")))
    assert list(_slots(documented)) == [1, 1, 28, 0, 0, 0]
    hour_borrow = as_period(interval(
        ymd_hms("1985-12-31 05:00:00"), ymd_hms("1986-02-01 03:00:00"),
    ))
    assert list(_slots(hour_borrow)) == [0, 1, 0, 22, 0, 0]
    # POSIXlt year 100 is not a leap year, so February 2000 contributes 28 days.
    assert list(_slots(as_period(interval(ymd("2000-01-28"), ymd("2000-03-01"))))) == [0, 1, 1, 0, 0, 0]
    # POSIXlt year 0 is a leap year, so February 1900 contributes 29 days.
    assert list(_slots(as_period(interval(ymd("1900-01-28"), ymd("1900-03-01"))))) == [0, 1, 2, 0, 0, 0]


def test_time_length_year_uses_the_anniversary():
    span = interval(ymd("1980-01-01"), ymd("2014-09-18"))
    got = float(np.asarray(time_length(span, "year")).reshape(-1)[0])
    assert abs(got - 34.712328767123289) < 1e-12


def test_mplus_rolls_back_to_the_last_valid_day():
    got = mplus(ymd_hms("2010-01-31 03:04:05"), period(month=1))
    assert float(np.asarray(got.seconds).reshape(-1)[0]) == 1267326245
    leap = mplus(ymd("2012-02-29"), years(1))
    assert float(np.asarray(leap.seconds).reshape(-1)[0]) == 1362009600
