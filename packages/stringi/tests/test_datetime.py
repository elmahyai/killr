"""Checks for stringi date-time and time-zone functions."""

from __future__ import annotations

import warnings

import pytest

from stringi._na import NA, is_na
from stringi.datetime import (
    stri_datetime_add,
    stri_datetime_add_assign,
    stri_datetime_create,
    stri_datetime_fields,
    stri_datetime_format,
    stri_datetime_fstr,
    stri_datetime_now,
    stri_datetime_parse,
    stri_datetime_symbols,
    stri_timezone_get,
    stri_timezone_info,
    stri_timezone_list,
    stri_timezone_set,
)


def test_create_matches_probed_instants():
    assert stri_datetime_create(2015, 1, 1, tz="UTC") == 1420070400.0
    assert stri_datetime_create(2015, 12, 31, 23, 59, 59.999, tz="UTC") == pytest.approx(
        1451606399.9990001
    )
    assert is_na(stri_datetime_create(2015, 2, 29, tz="UTC"))
    assert stri_datetime_create(2015, 2, 29, lenient=True, tz="UTC") == 1425168000.0
    assert (
        stri_datetime_create(5775, 8, 1, locale="@calendar=hebrew", tz="UTC")
        == 1426896000.0
    )
    assert stri_datetime_create([2015, NA], 1, 1, tz="UTC") == [1420070400.0, NA]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        assert stri_datetime_create(1e10, 1, 1, tz="UTC") is NA


def test_fractional_seconds_round_like_r():
    assert stri_datetime_create(2015, 1, 1, 0, 0, 0.0005, tz="UTC") == 1420070400.0
    created = stri_datetime_create(2015, 1, 1, 0, 0, 0.0015, tz="UTC")
    assert created == pytest.approx(1420070400.0020001)
    fields = stri_datetime_fields(created, tz="UTC", locale="en_US")
    assert fields["Millisecond"] == 2
    assert is_na(stri_datetime_create(2015, 1, 1, 0, 0, 1.9995, tz="UTC"))
    rolled = stri_datetime_create(2015, 1, 1, 0, 0, 59.9995, tz="UTC")
    assert stri_datetime_fields(rolled, tz="UTC")["Millisecond"] == 999


def test_add_uses_the_calendar():
    january = stri_datetime_create(2024, 1, 31, tz="UTC")
    assert stri_datetime_add(january, 1, "months", tz="UTC") == 1709164800.0
    start = stri_datetime_create(2015, 1, 31, tz="UTC")
    assert stri_datetime_add(start, 1, units="mo", tz="UTC") == 1425081600.0
    hebrew = stri_datetime_add(
        stri_datetime_create(2025, 4, 20, tz="UTC"),
        1,
        "years",
        tz="UTC",
        locale="@calendar=hebrew",
    )
    assert hebrew == 1775692800.0
    assert stri_datetime_add_assign(start, units="months", value=1, tz="UTC") == 1425081600.0
    assert stri_datetime_add([start, NA], [1, NA], units="days", tz="UTC")[1] is NA


def test_day_and_hour_differ_across_dst():
    moment = stri_datetime_create(2015, 3, 28, 12, 0, 0, tz="Europe/Brussels")
    plus_day = stri_datetime_add(moment, 1, "days", tz="Europe/Brussels")
    plus_hours = stri_datetime_add(moment, 24, "hours", tz="Europe/Brussels")
    assert (
        stri_datetime_format(plus_day, "uuuu-MM-dd HH:mm:ss Z", tz="Europe/Brussels")
        == "2015-03-29 12:00:00 +0200"
    )
    assert (
        stri_datetime_format(plus_hours, "uuuu-MM-dd HH:mm:ss Z", tz="Europe/Brussels")
        == "2015-03-29 13:00:00 +0200"
    )


def test_fields_of_a_fixed_instant():
    instant = stri_datetime_create(2015, 12, 31, 23, 59, 59, tz="UTC")
    fields = stri_datetime_fields(instant, tz="UTC", locale="en_US")
    assert fields["Year"] == 2015
    assert fields["Month"] == 12
    assert fields["Day"] == 31
    assert fields["Hour"] == 23
    assert fields["Hour12"] == 11
    assert fields["AmPm"] == 2
    assert fields["Era"] == 2
    assert fields["DayOfWeek"] == 5
    missing = stri_datetime_fields([instant, NA], tz="UTC")
    assert missing["Year"][1] is NA


def test_format_styles_and_patterns():
    instant = stri_datetime_create(2015, 12, 31, 23, 59, 59, tz="UTC")
    assert stri_datetime_format(instant, "uuuu-MM-dd HH:mm:ss", tz="UTC") == "2015-12-31 23:59:59"
    assert (
        stri_datetime_format(instant, "date_full", tz="UTC", locale="en_US")
        == "Thursday, December 31, 2015"
    )
    assert stri_datetime_format(instant, "time_full", tz="UTC", locale="en_US") == (
        "11:59:59\u202fPM Coordinated Universal Time"
    )
    assert (
        stri_datetime_format(
            instant, "yyyy.MM.dd 'at' HH:mm:ss zzz", tz="Europe/Warsaw", locale="pl_PL"
        )
        == "2016.01.01 at 00:59:59 CET"
    )
    assert stri_datetime_format([instant, NA], ["uuuu", NA], tz="UTC") == ["2015", NA]
    assert stri_datetime_format("2015-01-01", "uuuu-MM-dd HH:mm:ss", tz="UTC") == (
        "2014-12-31 23:00:00"
    )


def test_parse_and_fstr():
    assert stri_datetime_parse("2015-02-28", "yyyy-MM-dd", tz="UTC") == 1425081600.0
    assert is_na(stri_datetime_parse("2015-02-29", "yyyy-MM-dd", tz="UTC"))
    assert stri_datetime_parse("2015-02-29", "yyyy-MM-dd", lenient=True, tz="UTC") == 1425168000.0
    assert (
        stri_datetime_parse("19 lipca 2015", "date_long", locale="pl_PL", tz="Europe/Warsaw")
        == 1437256800.0
    )
    assert stri_datetime_fstr("%Y-%m-%d %H:%M:%S") == "yyyy'-'MM'-'dd' 'HH':'mm':'ss"
    assert stri_datetime_fstr("it's %Y") == "'it\\'s 'yyyy"
    assert stri_datetime_fstr("datetime_full", ignore_special=False) == "datetime_full"
    assert stri_datetime_fstr("date_full", ignore_special=1) == "date_full"
    assert stri_datetime_fstr("NA") == "'NA'"
    assert stri_datetime_fstr(NA) is NA
    assert stri_datetime_fstr("%n") == "\n"


def test_symbols_follow_locale_and_calendar():
    english = stri_datetime_symbols("en_US")
    assert english["Month"][0] == "January"
    assert english["Weekday"][0] == "Sunday"
    assert english["Quarter"][0] == "1st quarter"
    assert english["Era"] == ["Before Christ", "Anno Domini"]
    polish = stri_datetime_symbols("pl_PL", context="format", width="wide")
    assert polish["Month"][0] == "stycznia"
    hebrew = stri_datetime_symbols("@calendar=hebrew")
    assert hebrew["Month"][0] == "Tishri"
    assert len(hebrew["Month"]) == 14
    narrow = stri_datetime_symbols("en_US", width="narrow")
    assert narrow["Era"] == ["B", "A"]
    japanese = stri_datetime_symbols("@calendar=japanese", width="narrow")
    assert japanese["Era"][-5:] == ["M", "T", "S", "H", "R"]
    thai = stri_datetime_symbols("th_TH_TRADITIONAL")
    assert thai["Era"] == ["ปีก่อนคริสตกาล", "คริสต์ศักราช"]


def test_time_zones():
    assert stri_timezone_list(region="PL") == ["Europe/Warsaw", "Poland"]
    assert len(stri_timezone_list(offset=1)) == 52
    assert "Asia/Kolkata" in stri_timezone_list(offset=5.5)
    assert stri_timezone_list(region="") == []
    zones = stri_timezone_list()
    assert zones[0] == "ACT"
    assert zones[-1] == "Zulu"
    assert len(zones) == 637
    info = stri_timezone_info("Europe/London", locale="en_US")
    assert info["Name"] == "Greenwich Mean Time"
    assert info["Name.Daylight"] == "British Summer Time"
    assert info["Name.Windows"] == "GMT Standard Time"
    assert info["RawOffset"] == 0
    assert info["UsesDaylightTime"] is True
    utc = stri_timezone_info("UTC", locale="en_US")
    assert is_na(utc["Name.Daylight"])
    previous = stri_timezone_get()
    try:
        returned = stri_timezone_set("Pacific/Auckland")
        assert returned == previous
        assert stri_timezone_get() == "Pacific/Auckland"
    finally:
        stri_timezone_set(previous)
    assert stri_timezone_get() == previous


def test_now_is_one_finite_instant():
    instant = stri_datetime_now()
    assert isinstance(instant, float)
    assert instant > 1_700_000_000
    fields = stri_datetime_fields(instant, tz="UTC")
    assert isinstance(fields["Year"], int)
    assert 1 <= fields["Month"] <= 12


def test_errors_and_warnings():
    with pytest.raises(ValueError, match="incorrect option for `units`"):
        stri_datetime_add(1420070400, 1, units="m", tz="UTC")
    with pytest.raises(ValueError, match="incorrect time zone identifier"):
        stri_timezone_set("Not/AZone")
    with pytest.raises(ValueError, match="missing values in argument `lenient`"):
        stri_datetime_create(2015, 1, 1, lenient=NA, tz="UTC")
    with pytest.raises(ValueError, match="conversion specifier '%Q' is not valid"):
        stri_datetime_fstr("%Q")
    with pytest.raises(ValueError, match="POSIXct"):
        stri_datetime_format(object(), tz="UTC")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        stri_datetime_fstr("%c")
        stri_datetime_create([2015, 2016], 1, [1, 2, 3], tz="UTC")
    texts = [str(item.message) for item in caught]
    assert any("might be non-portable" in text for text in texts)
    assert any("not a multiple of shorter object length" in text for text in texts)
