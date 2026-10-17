"""Locales and date-name tables from readr's ICU symbols."""

from __future__ import annotations

import json
from pathlib import Path

from zoneinfo import ZoneInfo, available_timezones

_SYMBOLS = json.loads(
    (Path(__file__).with_name("date_symbols.json")).read_text(encoding="utf-8")
)
_ZONES = set(available_timezones())
_ZONES.update({"UTC", "GMT", "Etc/UTC", "Etc/GMT"})


class DateNames:
    """Weekday and month names for one language. Days start on Sunday."""

    def __init__(self, mon, mon_ab, day, day_ab, am_pm):
        self.mon = list(mon)
        self.mon_ab = list(mon_ab)
        self.day = list(day)
        self.day_ab = list(day_ab)
        self.am_pm = list(am_pm)

    def __str__(self) -> str:
        if self.day == self.day_ab:
            days = ", ".join(self.day)
        else:
            days = ", ".join(
                f"{full} ({short})" for full, short in zip(self.day, self.day_ab)
            )
        if self.mon == self.mon_ab:
            months = ", ".join(self.mon)
        else:
            months = ", ".join(
                f"{full} ({short})" for full, short in zip(self.mon, self.mon_ab)
            )
        am_pm = "/".join(self.am_pm)
        return f"<date_names>\nDays:   {days}\nMonths: {months}\nAM/PM:  {am_pm}"

    __repr__ = __str__


def date_names(mon, mon_ab=None, day=None, day_ab=None, am_pm=("AM", "PM")):
    """Build date names from the twelve months and seven weekdays."""
    mon = list(mon)
    if len(mon) != 12:
        raise ValueError("mon must have length 12")
    mon_ab = list(mon if mon_ab is None else mon_ab)
    if len(mon_ab) != 12:
        raise ValueError("mon_ab must have length 12")
    if day is None:
        raise TypeError("day is required")
    day = list(day)
    if len(day) != 7:
        raise ValueError("day must have length 7")
    day_ab = list(day if day_ab is None else day_ab)
    if len(day_ab) != 7:
        raise ValueError("day_ab must have length 7")
    am_pm = list(am_pm)
    return DateNames(mon, mon_ab, day, day_ab, am_pm)


def date_names_langs():
    """Language codes that `date_names_lang` knows."""
    return list(_SYMBOLS)


def date_names_lang(language):
    """Date names for a language code such as ``en`` or ``fr``."""
    if not isinstance(language, str) or not language:
        raise TypeError("language must be a string")
    symbols = _SYMBOLS.get(language)
    if symbols is None:
        raise ValueError(f"Unknown language '{language}'")
    return DateNames(
        symbols["mon"],
        symbols["mon_ab"],
        symbols["day"],
        symbols["day_ab"],
        symbols["am_pm"],
    )


def _known_zone(name: str) -> bool:
    if name in _ZONES:
        return True
    try:
        ZoneInfo(name)
    except Exception:
        return False
    return True


class Locale:
    """Decimal marks, time zone, encoding, and date-name language."""

    def __init__(
        self,
        date_names,
        date_format,
        time_format,
        decimal_mark,
        grouping_mark,
        tz,
        encoding,
    ):
        self.date_names = date_names
        self.date_format = date_format
        self.time_format = time_format
        self.decimal_mark = decimal_mark
        self.grouping_mark = grouping_mark
        self.tz = tz
        self.encoding = encoding

    def __str__(self) -> str:
        sample = f"123{self.grouping_mark}456{self.decimal_mark}78"
        return (
            "<locale>\n"
            f"Numbers:  {sample}\n"
            f"Formats:  {self.date_format} / {self.time_format}\n"
            f"Timezone: {self.tz}\n"
            f"Encoding: {self.encoding}\n"
            f"{self.date_names}"
        )

    __repr__ = __str__


def locale(
    date_names="en",
    date_format="%AD",
    time_format="%AT",
    decimal_mark=".",
    grouping_mark=None,
    tz="UTC",
    encoding="UTF-8",
    asciify=False,
):
    """Create a locale. The default matches R: US English and UTC."""
    if isinstance(date_names, str):
        names = date_names_lang(date_names)
    elif isinstance(date_names, DateNames):
        names = date_names
    else:
        raise TypeError("date_names must be a language code or date names")
    if asciify:
        names = _asciify(names)
    if grouping_mark is None:
        grouping_mark = "," if decimal_mark == "." else "."
    if decimal_mark not in (".", ","):
        raise ValueError("decimal_mark must be '.' or ','")
    if not isinstance(grouping_mark, str):
        raise TypeError("grouping_mark must be a string")
    if decimal_mark == grouping_mark:
        raise ValueError("`decimal_mark` and `grouping_mark` must be different")
    zone = _check_tz(tz)
    _check_encoding(encoding)
    return Locale(
        names, date_format, time_format, decimal_mark, grouping_mark, zone, encoding
    )


def _check_tz(tz) -> str:
    if not isinstance(tz, str):
        raise TypeError("tz must be a string")
    if tz == "":
        from datetime import datetime

        tz = datetime.now().astimezone().tzname() or "UTC"
        if not tz or not _known_zone(tz):
            tz = "UTC"
    if not _known_zone(tz):
        raise ValueError(f"Unknown TZ {tz}")
    return tz


def _check_encoding(encoding) -> None:
    if not isinstance(encoding, str) or not encoding:
        raise TypeError("encoding must be a string")
    if encoding in ("latin1", "UTF-8", "utf-8", "ASCII"):
        return
    try:
        "x".encode(encoding)
    except LookupError:
        warnings_unknown(encoding)


def warnings_unknown(encoding: str) -> None:
    import warnings

    warnings.warn(f'Unknown encoding "{encoding}".', stacklevel=4)


def _asciify(names: DateNames) -> DateNames:
    from stringi.trans import stri_trans_general

    def convert(values):
        converted = stri_trans_general(list(values), id="latin-ascii")
        if isinstance(converted, str):
            return [converted]
        return list(converted)

    return DateNames(
        convert(names.mon),
        convert(names.mon_ab),
        convert(names.day),
        convert(names.day_ab),
        convert(names.am_pm),
    )


def default_locale():
    """The locale stored in the ``readr.default_locale`` option."""
    from withr._options import get_option, options

    current = get_option("readr.default_locale")
    if current is None:
        current = locale()
        options(**{"readr.default_locale": current})
    return current
