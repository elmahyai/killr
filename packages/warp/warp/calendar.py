"""Civil-date arithmetic copied from warp's C distance engine."""

from __future__ import annotations

import math

from warp.errors import WarpError

DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
DAYS_IN_MONTH_LEAP = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
DAYS_UP_TO_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)

_DAYS_FROM_2001 = -11323
_SMALLEST_DAYS = -2147483648 + 1 - _DAYS_FROM_2001
_YEAR_OFFSET_FROM_EPOCH = 30


def c_message(where: str, why: str) -> str:
    return f"In C function `{where}()`: {why}"


def floor_div(value: int, every: int) -> int:
    """Group a signed count. `every` is positive, so this is floor division."""
    if every == 1:
        return value
    return value // every


def is_leap_year(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def days_before_year_offset(year_offset: int) -> int:
    year = year_offset + 1969
    days = year * 365 + year // 4 - year // 100 + year // 400
    return days - 719162


def days_before_year_since_1900(year: int) -> int:
    year = year + 1900 - 1
    days = year * 365 + year // 4 - year // 100 + year // 400
    return days - 719162


def leap_years_before_and_including_year(year_offset: int) -> int:
    year = year_offset + 1969
    leaps = year // 4 - year // 100 + year // 400
    return leaps - 477


def convert_days_to_components(n: int) -> tuple[int, int, int, int]:
    """Days since 1970-01-01 to (year offset, month 0-11, day 0-30, yday)."""
    if n < _SMALLEST_DAYS:
        raise WarpError(
            c_message(
                "convert_days_to_components",
                "Integer overflow! "
                f"The smallest possible value for `n` is {_SMALLEST_DAYS}",
            )
        )

    n = _DAYS_FROM_2001 + n
    n_400, n = divmod(n, 146097)
    n_100, n = divmod(n, 36524)
    n_4, n = divmod(n, 1461)
    n_1, n = divmod(n, 365)

    year = 1 + n_400 * 400 + n_100 * 100 + n_4 * 4 + n_1
    if n_1 == 4 or n_100 == 4:
        return (year - 1 + _YEAR_OFFSET_FROM_EPOCH, 11, 30, 365)

    yday = n
    leap = n_1 == 3 and (n_4 != 24 or n_100 == 3)
    month = (n + 50) >> 5
    preceding = DAYS_UP_TO_MONTH[month - 1] + (1 if leap and month > 2 else 0)
    if preceding > n:
        month -= 1
        preceding -= DAYS_IN_MONTH[month - 1] + (1 if leap and month == 2 else 0)
    day = n - preceding
    return (year + _YEAR_OFFSET_FROM_EPOCH, month - 1, day, yday)


def yday_leap_adjustment(year_offset: int, yday: int, origin_leap: bool) -> int:
    if yday < 58:
        return 0
    year_is_leap = is_leap_year(year_offset + 1970)
    if origin_leap:
        return 0 if year_is_leap else -1
    return 1 if year_is_leap else 0


def compute_yday_distance(
    days_since_epoch: int,
    year_offset: int,
    yday: int,
    origin_year_offset: int,
    origin_yday: int,
    origin_leap: bool,
    units_in_leap_year: int,
    units_in_non_leap_year: int,
    leap_years_before_origin: int,
    every: int,
) -> int:
    origin_yday_adjusted = origin_yday + yday_leap_adjustment(
        year_offset, yday, origin_leap
    )
    last_origin_year_offset = year_offset
    if yday < origin_yday_adjusted:
        last_origin_year_offset -= 1

    last_origin = days_before_year_offset(last_origin_year_offset) + origin_yday
    last_origin += yday_leap_adjustment(
        last_origin_year_offset, origin_yday, origin_leap
    )
    units_in_year = (days_since_epoch - last_origin) // every
    years_between = last_origin_year_offset - origin_year_offset
    leap_between = (
        leap_years_before_and_including_year(last_origin_year_offset)
        - leap_years_before_origin
    )
    non_leap_between = years_between - leap_between
    units_between = (
        units_in_leap_year * leap_between + units_in_non_leap_year * non_leap_between
    )
    return units_between + units_in_year


def _units_per_month(days: tuple[int, ...], every: int) -> list[int]:
    return [(day - 1) // every + 1 for day in days]


def compute_mday_distance(
    day: int,
    month: int,
    year_offset: int,
    origin_year_offset: int,
    units_leap_year: int,
    units_non_leap_year: int,
    units_month_leap: list[int],
    units_month_non_leap: list[int],
    units_up_to_origin_month: int,
    leap_years_before_origin: int,
    every: int,
) -> int:
    years_between = year_offset - origin_year_offset
    leap_between = (
        leap_years_before_and_including_year(year_offset) - leap_years_before_origin
    )
    non_leap_between = years_between - leap_between
    units_between = (
        leap_between * units_leap_year + non_leap_between * units_non_leap_year
    )
    units_month = (
        units_month_leap
        if is_leap_year(year_offset + 1970)
        else units_month_non_leap
    )
    units_up_to_month = sum(units_month[:month])
    return units_between - units_up_to_origin_month + units_up_to_month + day // every


def mday_tables(every: int, origin_year_offset: int, origin_month: int):
    units_non_leap = _units_per_month(DAYS_IN_MONTH, every)
    units_leap = _units_per_month(DAYS_IN_MONTH_LEAP, every)
    per_non_leap = sum(units_non_leap)
    per_leap = sum(units_leap)
    origin_units = units_leap if is_leap_year(origin_year_offset + 1970) else units_non_leap
    up_to_origin = sum(origin_units[:origin_month])
    leaps = leap_years_before_and_including_year(origin_year_offset)
    return units_leap, units_non_leap, per_leap, per_non_leap, up_to_origin, leaps


def guarded_floor(value: float) -> int:
    value *= 1e6
    value = math.trunc(value)
    value *= 1e-6
    value += 1e-7
    value = math.floor(value)
    return int(value)


def guarded_floor_to_millisecond(value: float) -> int:
    value *= 1e6
    value = math.trunc(value)
    value *= 1e-6
    value += 1e-7
    value *= 1e3
    value = math.floor(value)
    return int(value)
