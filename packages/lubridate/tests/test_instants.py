"""Fixed cases from lubridate 1.9.5."""

from datetime import datetime, timezone

from lubridate import (
    date,
    floor_date,
    force_tz,
    force_tzs,
    wday,
    year,
    year_set,
)
from timechange.civil import Posixct


def _utc(year, month, day, hour=0, minute=0, second=0):
    stamp = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp()
    return Posixct(stamp, "UTC")


def test_components_of_a_utc_day():
    instant = _utc(2009, 9, 2)
    assert int(year(instant)) == 2009
    assert int(wday(instant)) == 4
    assert int(wday(instant, week_start=1)) == 3
    assert float(date(instant).days) == 14489
    assert float(floor_date(instant, "month").seconds) == 1251763200


def test_year_replacement_and_a_skipped_hour():
    instant = _utc(2009, 9, 2)
    assert float(year_set(instant, 2010).seconds) == 1283385600
    gap = Posixct(1268532305, "UTC")
    assert float(force_tz(gap, "America/New_York", roll_dst="boundary").seconds) == 1268550000
    both = force_tzs(Posixct([1268532305, 1268532305], "UTC"), ["America/New_York", "Europe/Amsterdam"])
    assert both.seconds[0] != both.seconds[0]
    assert float(both.seconds[1]) == 1268528705
