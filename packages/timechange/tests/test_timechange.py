"""Fixed cases taken from timechange 0.4.0."""

import math

from timechange import (
    time_add,
    time_at_tz,
    time_ceiling,
    time_clock_at_tz,
    time_floor,
    time_force_tz,
    time_get,
    time_round,
    time_subtract,
    time_update,
)
from timechange.civil import Posixct


def test_spring_forward_addition():
    instant = Posixct(1268546523, "America/New_York")
    assert time_add(instant, hour=1, minute=50, roll_dst="post").seconds == 1268553123
    assert time_add(instant, hour=1, minute=50, roll_dst="pre").seconds == 1268549523
    assert math.isnan(time_add(instant, hour=1, minute=50, roll_dst="NA").seconds)


def test_fallback_vector():
    instant = Posixct([1414901700, 1414912500], "America/New_York")
    got = time_add(instant, hour=[1, -1], roll_dst="xlast").seconds
    assert list(got) == [1414908900, 1414905300]


def test_month_roll_and_update():
    instant = Posixct(949302123, "America/Chicago")
    assert time_add(instant, month=1, roll_month="preday").seconds == 951807723
    assert time_update(instant, month=2, roll_month="boundary").seconds == 951890400
    assert time_subtract(instant, day=1, hour=2).seconds == 949208523


def test_zones_and_components():
    instant = Posixct(949302123, "America/Chicago")
    got = time_get(instant)
    assert [int(got[name]) for name in ("year", "month", "mday", "wday", "hour")] == [2000, 1, 31, 0, 1]
    assert time_clock_at_tz(instant) == 3723
    assert float(time_at_tz(instant, "UTC").seconds) == 949302123
    forced = time_force_tz(Posixct(1268532305, "UTC"), "America/New_York", roll_dst="boundary")
    assert forced.seconds == 1268550000


def test_rounding():
    instant = Posixct(1249300919.23, "UTC")
    assert time_floor(instant, "minute").seconds == 1249300860
    assert time_ceiling(instant, "minute").seconds == 1249300920
    assert time_round(instant, "minute").seconds == 1249300920
    on_month = Posixct(946684800.0, "UTC")
    assert time_ceiling(on_month, "month", change_on_boundary=False).seconds == 946684800
