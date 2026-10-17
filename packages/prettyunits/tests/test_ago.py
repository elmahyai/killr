"""Rows from prettyunits tests/testthat/test-vague-dt.r."""

from datetime import datetime, timedelta

import pytest

from prettyunits._difftime import Difftime
from prettyunits.ago import time_ago, vague_dt

# Amount, unit, default, short, terse. Same rows as the R test.
CASES = [
    (1, "secs", "moments ago", "<1 min", " 1s"),
    (30, "secs", "less than a minute ago", "<1 min", "30s"),
    (50, "secs", "about a minute ago", "1 min", " 1m"),
    (14, "mins", "14 minutes ago", "14 min", "14m"),
    (70, "mins", "about an hour ago", "1 hour", " 1h"),
    (5, "hours", "5 hours ago", "5 hours", " 5h"),
    (25, "hours", "a day ago", "1 day", " 1d"),
    (5, "days", "5 days ago", "5 day", " 5d"),
    (30, "days", "about a month ago", "1 mon", " 1M"),
    (30 * 3, "days", "3 months ago", "3 mon", " 3M"),
    (365, "days", "about a year ago", "1 year", " 1y"),
    (365 * 10, "days", "10 years ago", "10 years", "10y"),
]

_SCALE = {"secs": 1, "mins": 60, "hours": 3600, "days": 86400}


def _stamp(amount, units):
    return datetime.now() - timedelta(seconds=amount * _SCALE[units])


@pytest.mark.parametrize("amount,units,default,short,terse", CASES)
def test_vague_dt_formats(amount, units, default, short, terse):
    dt = Difftime(amount, units=units)
    assert vague_dt(dt) == default
    assert vague_dt(dt, format="short") == short
    assert vague_dt(dt, format="terse") == terse


@pytest.mark.parametrize("amount,units,default,short,terse", CASES)
def test_time_ago_formats(amount, units, default, short, terse):
    stamp = _stamp(amount, units)
    assert time_ago(stamp) == default
    assert time_ago(stamp, format="short") == short
    assert time_ago(stamp, format="terse") == terse


def test_vague_dt_empty():
    assert vague_dt(Difftime([], units="secs")) == []


def test_empty_ignores_a_bad_format():
    assert vague_dt(Difftime([], units="secs"), format="nope") == []


def test_time_ago_two_timestamps():
    now = datetime.now()
    stamps = [now - timedelta(seconds=60), now - timedelta(seconds=3600)]
    assert time_ago(stamps) == ["about a minute ago", "about an hour ago"]


def test_thirty_days_short_and_terse():
    dt = Difftime(30, units="days")
    assert vague_dt(dt, format="short") == "1 mon"
    assert vague_dt(dt, format="terse") == " 1M"


def test_format_prefixes():
    dt = Difftime(5, units="days")
    assert vague_dt(dt, format="d") == "5 days ago"
    assert vague_dt(dt, format="s") == "5 day"
    assert vague_dt(dt, format="t") == " 5d"


def test_time_ago_choice_vector_selects_default():
    stamp = datetime.now() - timedelta(days=5)
    choices = ["default", "short", "terse"]
    assert time_ago([stamp, stamp], format=choices) == ["5 days ago", "5 days ago"]


def test_vague_dt_length_two_errors():
    with pytest.raises(ValueError, match="the condition has length > 1"):
        vague_dt(Difftime([30, 5], units="days"))


def test_vague_dt_rejects_non_difftime():
    with pytest.raises(ValueError):
        vague_dt(30)


def test_terse_rounds_with_r_round():
    assert vague_dt(Difftime(49.6, units="secs"), format="terse") == "50s"


def test_one_week_is_seven_days():
    assert vague_dt(Difftime(1, units="weeks")) == "7 days ago"
