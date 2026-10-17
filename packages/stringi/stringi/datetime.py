"""Date-time and time-zone functions from stringi 1.8.9.

A POSIXct instant is a number of seconds since 1970-01-01 00:00:00 UTC.
PyICU's calendar and formatters take that same number of seconds.
A missing instant or a missing string is ``stringi._na.NA``. The string
``"NA"`` is text. ``None`` is R's ``NULL``.

Time zones are ICU zone identifiers. The default zone is the ICU default,
and ``stri_timezone_set`` changes it for the process.
"""

from __future__ import annotations

import ctypes
import math
import re
import struct
import warnings

import icu

from stringi._na import NA, is_na


class _Missing:
    def __repr__(self) -> str:
        return "MISSING"


_MISSING = _Missing()
_INT_MIN = -2147483648
_INT_MAX = 2147483647

_UNITS = (
    "years",
    "months",
    "weeks",
    "days",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
)
_UNIT_FIELD = {
    "years": icu.UCalendarDateFields.YEAR,
    "months": icu.UCalendarDateFields.MONTH,
    "weeks": icu.UCalendarDateFields.WEEK_OF_YEAR,
    "days": icu.UCalendarDateFields.DATE,
    "hours": icu.UCalendarDateFields.HOUR_OF_DAY,
    "minutes": icu.UCalendarDateFields.MINUTE,
    "seconds": icu.UCalendarDateFields.SECOND,
    "milliseconds": icu.UCalendarDateFields.MILLISECOND,
}

_FIELD_ORDER = (
    "Year",
    "Month",
    "Day",
    "Hour",
    "Minute",
    "Second",
    "Millisecond",
    "WeekOfYear",
    "WeekOfMonth",
    "DayOfYear",
    "DayOfWeek",
    "Hour12",
    "AmPm",
    "Era",
)
_FIELD_ID = {
    "Year": icu.UCalendarDateFields.EXTENDED_YEAR,
    "Month": icu.UCalendarDateFields.MONTH,
    "Day": icu.UCalendarDateFields.DATE,
    "Hour": icu.UCalendarDateFields.HOUR_OF_DAY,
    "Minute": icu.UCalendarDateFields.MINUTE,
    "Second": icu.UCalendarDateFields.SECOND,
    "Millisecond": icu.UCalendarDateFields.MILLISECOND,
    "WeekOfYear": icu.UCalendarDateFields.WEEK_OF_YEAR,
    "WeekOfMonth": icu.UCalendarDateFields.WEEK_OF_MONTH,
    "DayOfYear": icu.UCalendarDateFields.DAY_OF_YEAR,
    "DayOfWeek": icu.UCalendarDateFields.DAY_OF_WEEK,
    "Hour12": icu.UCalendarDateFields.HOUR,
    "AmPm": icu.UCalendarDateFields.AM_PM,
    "Era": icu.UCalendarDateFields.ERA,
}
_PLUS_ONE = {"Month", "AmPm", "Era"}

_STYLES = (
    "date_full",
    "date_long",
    "date_medium",
    "date_short",
    "date_relative_full",
    "date_relative_long",
    "date_relative_medium",
    "date_relative_short",
    "time_full",
    "time_long",
    "time_medium",
    "time_short",
    "time_relative_full",
    "time_relative_long",
    "time_relative_medium",
    "time_relative_short",
    "datetime_full",
    "datetime_long",
    "datetime_medium",
    "datetime_short",
    "datetime_relative_full",
    "datetime_relative_long",
    "datetime_relative_medium",
    "datetime_relative_short",
)
_STYLE_VALUE = (0, 1, 2, 3, 128, 129, 130, 131)
_RELATIVE = 128

_DISPLAY = {
    "short": icu.TimeZone.SHORT,
    "long": icu.TimeZone.LONG,
    "generic_short": icu.TimeZone.SHORT_GENERIC,
    "generic_long": icu.TimeZone.LONG_GENERIC,
    "gmt_short": icu.TimeZone.SHORT_GMT,
    "gmt_long": icu.TimeZone.LONG_GMT,
    "common": icu.TimeZone.SHORT_COMMONLY_USED,
    "generic_location": icu.TimeZone.GENERIC_LOCATION,
}
_CONTEXTS = ("format", "standalone")
_WIDTHS = ("abbreviated", "wide", "narrow")

_FSTR = {
    "U": "ww",
    "W": "ww",
    "g": "yy",
    "G": "Y",
    "a": "ccc",
    "A": "cccc",
    "b": "MMM",
    "B": "MMMM",
    "c": "eee MMM d HH:mm:ss yyyy",
    "d": "dd",
    "D": "MM/dd/yy",
    "e": "d",
    "F": "yyyy-MM-dd",
    "h": "MMM",
    "H": "HH",
    "I": "hh",
    "j": "D",
    "m": "MM",
    "M": "mm",
    "n": "\n",
    "p": "a",
    "r": "hh:mm:ss",
    "R": "HH:mm",
    "S": "ss",
    "t": "\t",
    "T": "HH:mm:ss",
    "u": "c",
    "V": "ww",
    "w": "c",
    "x": "yy/MM/dd",
    "X": "HH:mm:ss",
    "y": "yy",
    "Y": "yyyy",
    "z": "Z",
    "Z": "z",
}
_PROBLEMATIC = set("UVxXuwrgGc")
_SPECIAL = {
    f"'{kind}_{width}'": f"{kind}_{width}"
    for kind in ("date", "time", "datetime", "date_relative", "datetime_relative")
    for width in ("full", "long", "medium", "short")
}

_PARSE_CLEAR = (
    icu.UCalendarDateFields.MILLISECOND,
    icu.UCalendarDateFields.SECOND,
    icu.UCalendarDateFields.MINUTE,
    icu.UCalendarDateFields.AM_PM,
    icu.UCalendarDateFields.HOUR,
    icu.UCalendarDateFields.HOUR_OF_DAY,
    icu.UCalendarDateFields.MILLISECONDS_IN_DAY,
)

_POSIX_FORMATS = (
    re.compile(r"^(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+(?:\.\d+)?)$"),
    re.compile(r"^(\d+)/(\d+)/(\d+) (\d+):(\d+):(\d+(?:\.\d+)?)$"),
    re.compile(r"^(\d+)-(\d+)-(\d+) (\d+):(\d+)$"),
    re.compile(r"^(\d+)/(\d+)/(\d+) (\d+):(\d+)$"),
    re.compile(r"^(\d+)-(\d+)-(\d+)$"),
    re.compile(r"^(\d+)/(\d+)/(\d+)$"),
)

# R fround (src/nmath/fround.c). Used for the millisecond of a fractional second.
_DBL_DIG = 15
_DBL_MAX_10_EXP = 308
_MAX_DIGITS = _DBL_MAX_10_EXP + _DBL_DIG
_LOG10_2 = math.log10(2.0)

_I18N = ctypes.CDLL("libicui18n.so.76")
_UC = ctypes.CDLL("libicuuc.so.76")
_GET_QUARTERS = _I18N._ZNK6icu_7617DateFormatSymbols11getQuartersERiNS0_13DtContextTypeENS0_11DtWidthTypeE
_GET_QUARTERS.restype = ctypes.c_void_p
_GET_QUARTERS.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_int,
    ctypes.c_int,
]
_GET_NARROW_ERAS = _I18N._ZNK6icu_7617DateFormatSymbols13getNarrowErasERi
_GET_NARROW_ERAS.restype = ctypes.c_void_p
_GET_NARROW_ERAS.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
_CANON = _UC.uloc_canonicalize_76
_CANON.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_int32),
]
_CANON.restype = ctypes.c_int32
_DEFAULT_LOCALE = _UC.uloc_getDefault_76
_DEFAULT_LOCALE.restype = ctypes.c_char_p


def stri_datetime_now():
    """Current instant as seconds since 1970-01-01 00:00:00 UTC.

    Leap seconds are ignored. The value changes with the clock.
    """

    return float(icu.Calendar.getNow())


def stri_datetime_create(
    year=None,
    month=None,
    day=None,
    hour=0,
    minute=0,
    second=0,
    lenient=False,
    tz=None,
    locale=None,
):
    """Build instants from calendar fields.

    ``None`` for a field means the current value of that field. The hour,
    minute, and second defaults are 0, not the current time. A missing
    field makes that instant missing. ``lenient`` rolls an invalid day
    forward; otherwise that instant is missing.
    """

    if any(item is None for item in (year, month, day, hour, minute, second)):
        current = stri_datetime_fields(stri_datetime_now(), tz=tz, locale=locale)
        if year is None:
            year = current["Year"]
        if month is None:
            month = current["Month"]
        if day is None:
            day = current["Day"]
        if hour is None:
            hour = current["Hour"]
        if minute is None:
            minute = current["Minute"]
        if second is None:
            second = current["Second"]

    years, year_scalar = _integer_vector(year, "year")
    months, month_scalar = _integer_vector(month, "month")
    days, day_scalar = _integer_vector(day, "day")
    hours, hour_scalar = _integer_vector(hour, "hour")
    minutes, minute_scalar = _integer_vector(minute, "minute")
    seconds, second_scalar = _double_vector(second, "second")
    count = _recycle(
        [len(years), len(months), len(days), len(hours), len(minutes), len(seconds)]
    )
    scalar = (
        year_scalar
        and month_scalar
        and day_scalar
        and hour_scalar
        and minute_scalar
        and second_scalar
    )
    if count == 0:
        return []
    lenient_value = _logical_1(lenient, "lenient")
    zone = _timezone(tz, "tz", allow_default=True)
    calendar = _calendar(locale, zone, lenient_value)
    out = []
    for i in range(count):
        parts = (
            years[i % len(years)],
            months[i % len(months)],
            days[i % len(days)],
            hours[i % len(hours)],
            minutes[i % len(minutes)],
            seconds[i % len(seconds)],
        )
        if any(is_na(part) for part in parts):
            out.append(NA)
            continue
        sec = parts[5]
        whole = math.floor(sec)
        millis = int(_r_round((sec - whole) * 1000.0, 0))
        calendar.set(icu.UCalendarDateFields.EXTENDED_YEAR, parts[0])
        calendar.set(icu.UCalendarDateFields.MONTH, parts[1] - 1)
        calendar.set(icu.UCalendarDateFields.DATE, parts[2])
        calendar.set(icu.UCalendarDateFields.HOUR_OF_DAY, parts[3])
        calendar.set(icu.UCalendarDateFields.MINUTE, parts[4])
        calendar.set(icu.UCalendarDateFields.SECOND, int(whole))
        calendar.set(icu.UCalendarDateFields.MILLISECOND, millis)
        out.append(_calendar_time(calendar))
    return _finish(out, scalar)


def stri_datetime_fields(time, tz=None, locale=None):
    """Calendar fields of each instant.

    ``tz`` defaults to the default zone. ``None`` passed explicitly is that
    same default; R also reads a ``tzone`` attribute when ``tz`` is missing,
    and here the argument is always passed. Columns are the fourteen fields
    stringi returns, with month, AM/PM, and era counted from 1.
    """

    seconds, scalar = _posix_vector(time, "time")
    zone = _timezone(tz, "tz", allow_default=True)
    calendar = _calendar(locale, zone, True)
    columns = {name: [] for name in _FIELD_ORDER}
    for instant in seconds:
        if is_na(instant):
            for name in _FIELD_ORDER:
                columns[name].append(NA)
            continue
        try:
            calendar.setTime(float(instant))
        except icu.ICUError:
            for name in _FIELD_ORDER:
                columns[name].append(NA)
            continue
        for name in _FIELD_ORDER:
            try:
                value = int(calendar.get(_FIELD_ID[name]))
            except icu.ICUError:
                value = NA
            else:
                if name in _PLUS_ONE and value is not NA:
                    value += 1
            columns[name].append(value)
    if scalar and seconds:
        return {name: values[0] for name, values in columns.items()}
    return columns


def stri_datetime_add(time, value=1, units="seconds", tz=None, locale=None):
    """Add calendar units to each instant.

    ``units`` is a unique prefix of years, months, weeks, days, hours,
    minutes, seconds, or milliseconds. Adding a day keeps the local time
    of day; adding 24 hours can cross a daylight-saving change.
    """

    return _datetime_add(time, value, units, tz, locale)


def stri_datetime_add_assign(
    time, units="seconds", tz=None, locale=None, value=_MISSING
):
    """Replacement form of ``stri_datetime_add``.

    ``value`` is the number of units. This is R's ``stri_datetime_add<-``.
    """

    if value is _MISSING:
        raise ValueError('argument "value" is missing, with no default')
    return _datetime_add(time, value, units, tz, locale)


def stri_datetime_format(time, format="uuuu-MM-dd HH:mm:ss", tz=None, locale=None):
    """Format instants with an ICU pattern or a named style.

    A style is ``date``, ``time``, or ``datetime``, optionally ``_relative``,
    then ``_full``, ``_long``, ``_medium``, or ``_short``. Anything else is
    an ICU pattern. A missing instant or a missing pattern stays missing.
    """

    seconds, time_scalar = _posix_vector(time, "time")
    patterns, format_scalar = _character_vector(format, "format")
    count = _recycle([len(seconds), len(patterns)])
    if count == 0:
        return []
    zone = _timezone(tz, "tz", allow_default=True)
    locale_id = _prepare_locale(locale, "locale")
    out = []
    cache_key = None
    formatter = None
    for i in range(count):
        instant = seconds[i % len(seconds)]
        pattern = patterns[i % len(patterns)]
        if is_na(instant) or is_na(pattern):
            out.append(NA)
            continue
        if pattern != cache_key:
            cache_key = pattern
            formatter = _date_format(pattern, locale_id)
            formatter.setTimeZone(zone)
        out.append(formatter.format(float(instant)))
    return _finish(out, time_scalar and format_scalar)


def stri_datetime_parse(
    str, format="uuuu-MM-dd HH:mm:ss", lenient=False, tz=None, locale=None
):
    """Parse strings with an ICU pattern or a named style.

    Fields the pattern does not mention stay at midnight today in ``tz``.
    A string that does not match is missing. ``lenient`` accepts a day
    that rolls into the next month.
    """

    texts, text_scalar = _character_vector(str, "str")
    patterns, format_scalar = _character_vector(format, "format")
    count = _recycle([len(texts), len(patterns)])
    if count == 0:
        return []
    lenient_value = _logical_1(lenient, "lenient")
    zone = _timezone(tz, "tz", allow_default=True)
    locale_id = _prepare_locale(locale, "locale")
    out = []
    cache_key = None
    formatter = None
    for i in range(count):
        text = texts[i % len(texts)]
        pattern = patterns[i % len(patterns)]
        if is_na(text) or is_na(pattern):
            out.append(NA)
            continue
        if pattern != cache_key:
            cache_key = pattern
            formatter = _date_format(pattern, locale_id)
            formatter.setTimeZone(zone)
        formatter.setLenient(lenient_value)
        calendar = formatter.getCalendar()
        calendar.setLenient(lenient_value)
        calendar.setTime(float(icu.Calendar.getNow()))
        for field in _PARSE_CLEAR:
            calendar.clear(field)
        position = icu.ParsePosition(0)
        formatter.parse(text, calendar, position)
        if position.getErrorIndex() >= 0:
            out.append(NA)
            continue
        out.append(_calendar_time(calendar))
    return _finish(out, text_scalar and format_scalar)


def stri_datetime_fstr(x, ignore_special=True):
    """Turn a ``strptime`` pattern into an ICU pattern.

    ``%%`` becomes ``%``. ``%x``, ``%X``, ``%u``, ``%w``, ``%g``, ``%G``,
    ``%c``, ``%U``, and ``%V`` warn and are still converted. ``ignore_special``
    keeps a name such as ``date_full`` quoted. Only a length-1 logical
    ``TRUE`` counts as true; a number does not.
    """

    texts, scalar = _character_vector(x, "x")
    keep = _ignore_special(ignore_special)
    out = []
    for text in texts:
        if is_na(text):
            out.append(NA)
            continue
        converted = _fstr_one(text)
        if not keep and converted in _SPECIAL:
            converted = _SPECIAL[converted]
        out.append(converted)
    return _finish(out, scalar)


def stri_datetime_symbols(locale=None, context="standalone", width="wide"):
    """Month, weekday, quarter, AM/PM, and era names for a locale.

    ``context`` is ``format`` or ``standalone``. ``width`` is
    ``abbreviated``, ``wide``, or ``narrow``. A calendar keyword such as
    ``@calendar=hebrew`` selects that calendar's names.
    """

    context_name = _match_option(_string_1(context, "context"), _CONTEXTS, "context")
    width_name = _match_option(_string_1(width, "width"), _WIDTHS, "width")
    symbols = _date_symbols(locale)
    context_id = 0 if context_name == "format" else 1
    width_id = {"abbreviated": 0, "wide": 1, "narrow": 2}[width_name]
    months = list(
        symbols.getMonths(
            icu.DateFormatSymbols.FORMAT
            if context_id == 0
            else icu.DateFormatSymbols.STANDALONE,
            (
                icu.DateFormatSymbols.ABBREVIATED,
                icu.DateFormatSymbols.WIDE,
                icu.DateFormatSymbols.NARROW,
            )[width_id],
        )
    )
    weekdays = list(
        symbols.getWeekdays(
            icu.DateFormatSymbols.FORMAT
            if context_id == 0
            else icu.DateFormatSymbols.STANDALONE,
            (
                icu.DateFormatSymbols.ABBREVIATED,
                icu.DateFormatSymbols.WIDE,
                icu.DateFormatSymbols.NARROW,
            )[width_id],
        )
    )
    if weekdays and weekdays[0] == "":
        weekdays = weekdays[1:]
    if width_name == "wide":
        eras = list(symbols.getEraNames())
    elif width_name == "abbreviated":
        eras = list(symbols.getEras())
    else:
        eras = _symbol_strings(symbols, _GET_NARROW_ERAS, None, None)
    return {
        "Month": months,
        "Weekday": weekdays,
        "Quarter": _symbol_strings(symbols, _GET_QUARTERS, context_id, width_id),
        "AmPm": list(symbols.getAmPmStrings()),
        "Era": eras,
    }


def stri_timezone_list(region=NA, offset=NA):
    """ICU time zone identifiers, sorted as stringi sorts them.

    ``region`` is an ISO 3166 or UN M.49 code. ``offset`` is the raw
    offset from GMT in hours, before daylight saving. ``NA`` for either
    argument means every zone. The sort is primary strength, numeric,
    locale ``en_US``.
    """

    region_value = _region_arg(region)
    offset_value = _offset_arg(offset)
    if region_value == "":
        return []
    found = list(icu.TimeZone.createEnumeration())
    if not is_na(region_value):
        found = [zone_id for zone_id in found if icu.TimeZone.getRegion(zone_id) == region_value]
    if not is_na(offset_value):
        millis = ctypes.c_int32(int(offset_value * 1000.0 * 3600.0)).value
        found = [
            zone_id
            for zone_id in found
            if icu.TimeZone.createTimeZone(zone_id).getRawOffset() == millis
        ]
    collator = icu.Collator.createInstance(icu.Locale("en_US"))
    collator.setStrength(icu.Collator.PRIMARY)
    collator.setAttribute(
        icu.UCollAttribute.NUMERIC_COLLATION, icu.UCollAttributeValue.ON
    )
    found.sort(key=collator.getSortKey)
    return found


def stri_timezone_get():
    """ICU identifier of the current default time zone."""

    return stri_timezone_info()["ID"]


def stri_timezone_set(tz):
    """Set the default time zone and return the previous identifier.

    An empty string or an unknown identifier is an error. Restore the
    previous value when the change should not leak.
    """

    previous = stri_timezone_get()
    zone = _timezone(tz, "tz", allow_default=False)
    icu.TimeZone.setDefault(zone)
    return previous


def stri_timezone_info(tz=None, locale=None, display_type="long"):
    """Identifier, display name, Windows id, raw offset, and daylight use.

    ``display_type`` is a unique prefix of ``short``, ``long``,
    ``generic_short``, ``generic_long``, ``gmt_short``, ``gmt_long``,
    ``common``, or ``generic_location``. The daylight name is missing when
    the zone does not use daylight saving this year.
    """

    style_name = _match_option(
        _string_1(display_type, "display_type"), tuple(_DISPLAY), "display_type"
    )
    zone = _timezone(tz, "tz", allow_default=True)
    locale_id = _prepare_locale(locale, "locale")
    loc = icu.Locale.createFromName(locale_id)
    style = _DISPLAY[style_name]
    zone_id = zone.getID()
    daylight = bool(zone.useDaylightTime())
    windows = icu.TimeZone.getWindowsID(zone_id)
    if not windows:
        windows = NA
    return {
        "ID": zone_id,
        "Name": zone.getDisplayName(False, style, loc),
        "Name.Daylight": zone.getDisplayName(True, style, loc) if daylight else NA,
        "Name.Windows": windows,
        "RawOffset": zone.getRawOffset() / 1000.0 / 3600.0,
        "UsesDaylightTime": daylight,
    }


def _datetime_add(time, value, units, tz, locale):
    seconds, time_scalar = _posix_vector(time, "time")
    amounts, value_scalar = _integer_vector(value, "value")
    count = _recycle([len(seconds), len(amounts)])
    if count == 0:
        return []
    unit_name = _match_option(_string_1(units, "units"), _UNITS, "units")
    field = _UNIT_FIELD[unit_name]
    zone = _timezone(tz, "tz", allow_default=True)
    calendar = _calendar(locale, zone, True)
    out = []
    for i in range(count):
        instant = seconds[i % len(seconds)]
        amount = amounts[i % len(amounts)]
        if is_na(instant) or is_na(amount):
            out.append(NA)
            continue
        try:
            calendar.setTime(float(instant))
            calendar.add(field, int(amount))
        except icu.ICUError:
            out.append(NA)
            continue
        out.append(_calendar_time(calendar))
    return _finish(out, time_scalar and value_scalar)


def _finish(values, scalar):
    if scalar and len(values) == 1:
        return values[0]
    return values


def _calendar(locale, zone, lenient):
    locale_id = _prepare_locale(locale, "locale")
    calendar = icu.Calendar.createInstance(icu.Locale.createFromName(locale_id))
    calendar.setTimeZone(zone)
    calendar.setLenient(bool(lenient))
    return calendar


def _calendar_time(calendar):
    try:
        return float(calendar.getTime())
    except icu.ICUError:
        return NA


def _date_format(pattern, locale_id):
    matched = _match_index(pattern, _STYLES)
    loc = icu.Locale.createFromName(locale_id)
    if matched < 0:
        try:
            return icu.SimpleDateFormat(pattern, loc)
        except icu.ICUError as exc:
            raise ValueError(str(exc)) from exc
    style = _STYLE_VALUE[matched % 8]
    kind = matched // 8
    if kind == 0:
        return icu.DateFormat.createDateInstance(style, loc)
    if kind == 1:
        return icu.DateFormat.createTimeInstance(style & ~_RELATIVE, loc)
    return icu.DateFormat.createDateTimeInstance(style, style & ~_RELATIVE, loc)


def _date_symbols(locale):
    locale_id = _prepare_locale(locale, "locale")
    loc = icu.Locale.createFromName(locale_id)
    keyword = loc.getKeywordValue("calendar")
    if keyword:
        return icu.DateFormatSymbols(loc, keyword)
    # No calendar keyword: the one-argument constructor follows the locale
    # the way ICU's DateFormatSymbols(locale) does. The locale's default
    # calendar, from Calendar.createInstance, is a different choice.
    return icu.DateFormatSymbols(loc)


def _symbol_strings(symbols, function, context_id, width_id):
    pointer = struct.unpack_from("Q", ctypes.string_at(id(symbols) + 24, 8))[0]
    count = ctypes.c_int()
    if context_id is None:
        array = function(ctypes.c_void_p(pointer), ctypes.byref(count))
    else:
        array = function(
            ctypes.c_void_p(pointer), ctypes.byref(count), context_id, width_id
        )
    if not array or count.value < 0:
        raise RuntimeError("ICU date symbols could not be read")
    out = []
    for index in range(count.value):
        out.append(_unicode_string(array + index * 64))
    return out


def _unicode_string(address):
    flags = struct.unpack_from("<H", ctypes.string_at(address + 8, 2))[0]
    if (flags & 0xFFE0) == 0xFFE0:
        length = struct.unpack_from("<i", ctypes.string_at(address + 12, 4))[0]
    else:
        length = flags >> 5
    if length < 0 or length > 100000:
        raise RuntimeError("ICU string length is out of range")
    if length == 0:
        return ""
    if flags & 2:
        raw = ctypes.string_at(address + 10, length * 2)
    else:
        data = struct.unpack_from("Q", ctypes.string_at(address + 24, 8))[0]
        raw = ctypes.string_at(data, length * 2)
    return raw.decode("utf-16-le")


def _posix_vector(time, name):
    if time is None:
        raise ValueError(
            f"argument `{name}` should be an object of class POSIXct "
            "(or an object coercible to)"
        )
    scalar = not isinstance(time, (list, tuple))
    items = [time] if scalar else list(time)
    if not items:
        return [], False
    kinds = set()
    for item in items:
        if is_na(item) or item is None:
            continue
        if isinstance(item, bool):
            raise ValueError(
                f"argument `{name}` should be an object of class POSIXct "
                "(or an object coercible to)"
            )
        if isinstance(item, (int, float)):
            kinds.add("num")
        elif isinstance(item, str):
            kinds.add("str")
        else:
            raise ValueError(
                f"argument `{name}` should be an object of class POSIXct "
                "(or an object coercible to)"
            )
    if len(kinds) > 1:
        raise ValueError(
            f"argument `{name}` should be an object of class POSIXct "
            "(or an object coercible to)"
        )
    if "str" in kinds:
        return _parse_posix_character(items), scalar
    out = []
    for item in items:
        if is_na(item) or item is None:
            out.append(NA)
        else:
            out.append(float(item))
    return out, scalar


def _parse_posix_character(items):
    present = [item for item in items if not is_na(item) and item is not None]
    if not present:
        return [NA for _ in items]
    chosen = None
    for pattern in _POSIX_FORMATS:
        if all(pattern.match(item) for item in present):
            chosen = pattern
            break
    if chosen is None:
        raise ValueError("character string is not in a standard unambiguous format")
    zone = icu.TimeZone.createDefault()
    calendar = icu.Calendar.createInstance(icu.Locale.getDefault())
    calendar.setTimeZone(zone)
    calendar.setLenient(False)
    out = []
    for item in items:
        if is_na(item) or item is None:
            out.append(NA)
            continue
        parts = chosen.match(item).groups()
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = int(parts[3]) if len(parts) > 3 else 0
        minute = int(parts[4]) if len(parts) > 4 else 0
        second = float(parts[5]) if len(parts) > 5 else 0.0
        whole = math.floor(second)
        millis = int(_r_round((second - whole) * 1000.0, 0))
        calendar.set(icu.UCalendarDateFields.EXTENDED_YEAR, year)
        calendar.set(icu.UCalendarDateFields.MONTH, month - 1)
        calendar.set(icu.UCalendarDateFields.DATE, day)
        calendar.set(icu.UCalendarDateFields.HOUR_OF_DAY, hour)
        calendar.set(icu.UCalendarDateFields.MINUTE, minute)
        calendar.set(icu.UCalendarDateFields.SECOND, int(whole))
        calendar.set(icu.UCalendarDateFields.MILLISECOND, millis)
        out.append(_calendar_time(calendar))
    return out


def _character_vector(value, name):
    if value is None:
        return [], True
    scalar = not isinstance(value, (list, tuple))
    items = [value] if scalar else list(value)
    out = []
    for item in items:
        if is_na(item) or item is None:
            out.append(NA)
        elif isinstance(item, str):
            out.append(item)
        elif isinstance(item, bool):
            out.append("TRUE" if item else "FALSE")
        elif isinstance(item, int):
            out.append(str(item))
        elif isinstance(item, float):
            out.append(_character_number(item))
        else:
            raise ValueError(
                f"argument `{name}` should be a character vector (or an object coercible to)"
            )
    return out, scalar


def _character_number(value):
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == math.trunc(value) and abs(value) < 2**53:
        return str(int(value))
    return str(value)


def _integer_vector(value, name):
    if value is None:
        return [], True
    scalar = not isinstance(value, (list, tuple))
    items = [value] if scalar else list(value)
    return [_as_integer(item, name) for item in items], scalar


def _double_vector(value, name):
    if value is None:
        return [], True
    scalar = not isinstance(value, (list, tuple))
    items = [value] if scalar else list(value)
    return [_as_double(item, name) for item in items], scalar


def _as_integer(value, name):
    if is_na(value) or value is None:
        return NA
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        if value > _INT_MAX or value <= _INT_MIN:
            warnings.warn(
                "NAs introduced by coercion to integer range",
                UserWarning,
                stacklevel=4,
            )
            return NA
        return value
    if isinstance(value, float):
        if (
            math.isnan(value)
            or math.isinf(value)
            or value > _INT_MAX
            or value <= _INT_MIN
        ):
            warnings.warn(
                "NAs introduced by coercion to integer range",
                UserWarning,
                stacklevel=4,
            )
            return NA
        return int(math.trunc(value))
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=4)
            return NA
        return _as_integer(number, name)
    raise ValueError(
        f"argument `{name}` should be an integer vector (or an object coercible to)"
    )


def _as_double(value, name):
    if is_na(value) or value is None:
        return NA
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=4)
            return NA
    raise ValueError(
        f"argument `{name}` should be a numeric vector (or an object coercible to)"
    )


def _string_1(value, name, allow_na=False):
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single character string; "
                "only the first element is used",
                UserWarning,
                stacklevel=3,
            )
        value = value[0]
    if value is None:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if is_na(value):
        if allow_na:
            return NA
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    raise ValueError(
        f"argument `{name}` should be a character vector (or an object coercible to)"
    )


def _logical_1(value, name):
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                f"argument `{name}` should be a single logical value; "
                "only the first element is used",
                UserWarning,
                stacklevel=3,
            )
        value = value[0]
    if is_na(value) or value is None:
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            raise ValueError(f"missing values in argument `{name}` is not supported")
        return value != 0
    if isinstance(value, str) and value in ("TRUE", "FALSE", "T", "F"):
        return value in ("TRUE", "T")
    raise ValueError(
        f"argument `{name}` should be a logical vector (or an object coercible to)"
    )


def _ignore_special(value):
    if isinstance(value, bool):
        return value is True
    if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], bool):
        return value[0] is True
    return False


def _region_arg(value):
    if is_na(value):
        return NA
    return _string_1(value, "region", allow_na=True)


def _offset_arg(value):
    if is_na(value):
        return NA
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument `offset` should be a non-empty vector")
        if len(value) > 1:
            warnings.warn(
                "argument `offset` should be a single numeric value; "
                "only the first element is used",
                UserWarning,
                stacklevel=3,
            )
        value = value[0]
    if value is None:
        raise ValueError("argument `offset` should be a non-empty vector")
    if is_na(value):
        return NA
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            "argument `offset` should be a numeric vector (or an object coercible to)"
        )
    if isinstance(value, float) and math.isnan(value):
        return NA
    return float(value)


def _timezone(tz, name, allow_default):
    if tz is None or tz == "":
        if not allow_default:
            raise ValueError("incorrect time zone identifier")
        return icu.TimeZone.createDefault()
    text = _string_1(tz, name)
    if text == "":
        if not allow_default:
            raise ValueError("incorrect time zone identifier")
        return icu.TimeZone.createDefault()
    zone = icu.TimeZone.createTimeZone(text)
    if zone.getID() == "Etc/Unknown":
        raise ValueError("incorrect time zone identifier")
    return zone


def _prepare_locale(locale, name):
    default = _default_locale()
    if locale is None:
        return default
    if isinstance(locale, (list, tuple)) and len(locale) == 0:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    text = _string_1(locale, name)
    if text == "":
        return default
    canon = _canonicalize(text).strip(" \t\r\n")
    if canon == "":
        return default
    if _is_c_locale(canon):
        return "en_US_POSIX"
    if canon.startswith("@"):
        return default + canon
    return canon


def _default_locale():
    raw = _DEFAULT_LOCALE()
    text = raw.decode() if raw else "en_US"
    if _is_c_locale(text):
        return "en_US_POSIX"
    return text


def _canonicalize(text):
    buffer = ctypes.create_string_buffer(256)
    status = ctypes.c_int32(0)
    needed = _CANON(text.encode(), buffer, 256, ctypes.byref(status))
    if needed >= 256:
        buffer = ctypes.create_string_buffer(needed + 1)
        status = ctypes.c_int32(0)
        needed = _CANON(text.encode(), buffer, needed + 1, ctypes.byref(status))
    if status.value > 0:
        raise ValueError("locale could not be set or selected")
    return buffer.raw[:needed].decode()


def _is_c_locale(text):
    return bool(text) and text[0] in "Cc" and (len(text) == 1 or text[1] == ".")


def _recycle(lengths):
    if any(length <= 0 for length in lengths):
        return 0
    longest = max(lengths)
    if any(longest % length != 0 for length in lengths):
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            UserWarning,
            stacklevel=3,
        )
    return longest


def _match_option(option, choices, name):
    index = _match_index(option, choices)
    if index < 0:
        raise ValueError(f"incorrect option for `{name}`")
    return choices[index]


def _match_index(option, choices):
    if option is None:
        return -1
    excluded = [False] * len(choices)
    for position, character in enumerate(option):
        for index, choice in enumerate(choices):
            if excluded[index]:
                continue
            if position >= len(choice) or choice[position] != character:
                excluded[index] = True
            elif position + 1 == len(choice) and position + 1 == len(option):
                return index
    found = -1
    for index, skip in enumerate(excluded):
        if skip:
            continue
        if found >= 0:
            return -1
        found = index
    return found


def _fstr_one(text):
    buf = []
    index = 0
    literal = False
    size = len(text)
    while index < size:
        character = text[index]
        if character == "'":
            if not literal:
                literal = True
                buf.append("'")
            buf.append("\\'")
            index += 1
            continue
        if character != "%":
            if not literal:
                literal = True
                buf.append("'")
            buf.append(character)
            index += 1
            continue
        index += 1
        if index >= size:
            raise ValueError("conversion specifier '%' is not valid")
        if text[index] == "%":
            if not literal:
                literal = True
                buf.append("'")
            buf.append("%")
            index += 1
            continue
        if literal:
            literal = False
            buf.append("'")
        spec = text[index]
        index += 1
        if spec in _PROBLEMATIC:
            warnings.warn(
                f"conversion specifier '%{spec}' might be non-portable/problematic",
                UserWarning,
                stacklevel=3,
            )
        replacement = _FSTR.get(spec)
        if replacement is None:
            raise ValueError(f"conversion specifier '%{spec}' is not valid")
        buf.append(replacement)
    if literal:
        buf.append("'")
    return "".join(buf)


def _logb(value):
    _mantissa, exponent = math.frexp(value)
    return float(exponent - 1)


def _nearbyint(value):
    if math.isnan(value) or math.isinf(value) or value == 0.0:
        return math.copysign(0.0, value) if value == 0.0 else value
    magnitude = abs(value)
    down = math.floor(magnitude)
    fraction = magnitude - down
    if fraction > 0.5:
        rounded = down + 1.0
    elif fraction < 0.5:
        rounded = down
    elif math.fmod(down, 2.0) == 0.0:
        rounded = down
    else:
        rounded = down + 1.0
    if rounded == 0.0:
        return math.copysign(0.0, value)
    return math.copysign(rounded, value)


def _r_round(value, digits=0):
    value = float(value)
    digits = float(digits)
    if math.isnan(value) or math.isnan(digits):
        return value + digits
    if math.isinf(value):
        return value
    if digits > _MAX_DIGITS or value == 0.0:
        return math.copysign(0.0, value) if value == 0.0 else value
    if digits < -_DBL_MAX_10_EXP:
        return 0.0
    if digits == 0.0:
        return _nearbyint(value)
    dig = int(math.floor(digits + 0.5))
    sign = -1.0 if value < 0.0 else 1.0
    magnitude = abs(value)
    log10x = _LOG10_2 * (0.5 + _logb(magnitude))
    if log10x + dig > _DBL_DIG:
        return sign * magnitude
    if dig <= _DBL_MAX_10_EXP:
        pow10 = 10.0**dig
        scaled = magnitude * pow10
        down_scaled = math.floor(scaled)
        down = down_scaled / pow10
        up = math.ceil(scaled) / pow10
    else:
        extra = dig - _DBL_MAX_10_EXP
        pow10 = 10.0**_DBL_MAX_10_EXP
        finer = 10.0**extra
        scaled = (magnitude * pow10) * finer
        down_scaled = math.floor(scaled)
        down = down_scaled / pow10 / finer
        up = math.ceil(scaled) / pow10 / finer
    distance_up = up - magnitude
    distance_down = magnitude - down
    odd = math.fmod(down_scaled, 2.0) == 1.0
    choose_up = distance_up < distance_down or (odd and distance_up == distance_down)
    return sign * (up if choose_up else down)
