"""Parsers for the atomic types readr reads out of text."""

from __future__ import annotations

import math
import warnings
from datetime import date, datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from readr.columns import Collector, collector_for_name
from readr.locale import Locale, default_locale

_TRUE = {"T", "t", "True", "TRUE", "true"}
_FALSE = {"F", "f", "False", "FALSE", "false"}
_INT_MIN = -2147483648
_INT_MAX = 2147483647


class Hms:
    """A time of day, stored as seconds since midnight. Printed like hms."""

    def __init__(self, seconds: float):
        self.seconds = float(seconds)

    def __repr__(self) -> str:
        return _format_hms(self.seconds)

    __str__ = __repr__

    def __eq__(self, other) -> bool:
        return isinstance(other, Hms) and self.seconds == other.seconds


class Factor:
    """Values drawn from a fixed set of levels."""

    def __init__(self, values, levels, ordered=False):
        self.values = list(values)
        self.levels = list(levels)
        self.ordered = ordered

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]


def _format_hms(seconds: float) -> str:
    sign = "-" if seconds < 0 else ""
    whole = int(abs(seconds))
    hour, rest = divmod(whole, 3600)
    minute, second = divmod(rest, 60)
    return f"{sign}{hour:02d}:{minute:02d}:{second:02d}"


class _Cursor:
    def __init__(self, text: str, loc: Locale):
        self.text = text
        self.index = 0
        self.end = len(text)
        self.loc = loc
        self.year = -1
        self.mon = 1
        self.day = 1
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.psec = 0.0
        self.am_pm = -1
        self.sign = 1
        self.compact = True
        self.tz = loc.tz
        self.offset_hours = 0
        self.offset_minutes = 0

    def done(self) -> bool:
        return self.index >= self.end

    def peek(self) -> str:
        return "" if self.done() else self.text[self.index]

    def take(self) -> str:
        character = self.text[self.index]
        self.index += 1
        return character

    def take_this(self, needed: str) -> bool:
        if self.done() or self.text[self.index] != needed:
            return False
        self.index += 1
        return True

    def skip_space(self) -> None:
        while not self.done() and self.text[self.index].isspace():
            self.index += 1

    def integer(self, width: int, exact: bool = True) -> int | None:
        if self.done() or self.peek() in "-+":
            return None
        start = self.index
        stop = min(self.end, start + width)
        if start >= stop or not self.text[start].isdigit():
            return None
        index = start
        while index < stop and self.text[index].isdigit():
            index += 1
        if exact and (index - start) != width:
            return None
        if index == start:
            return None
        value = int(self.text[start:index])
        self.index = index
        return value

    def number(self) -> float | None:
        if self.done() or self.peek() in "-+":
            return None
        start = self.index
        saw_digit = False
        saw_dot = False
        mark = self.loc.decimal_mark
        while self.index < self.end:
            character = self.text[self.index]
            if character.isdigit():
                saw_digit = True
                self.index += 1
                continue
            if character == mark and not saw_dot:
                saw_dot = True
                self.index += 1
                continue
            if character in "eE" and saw_digit:
                self.index += 1
                if not self.done() and self.peek() in "+-":
                    self.index += 1
                exp_start = self.index
                while not self.done() and self.peek().isdigit():
                    self.index += 1
                if self.index == exp_start:
                    self.index = start
                    return None
                continue
            break
        if not saw_digit:
            self.index = start
            return None
        token = self.text[start:self.index].replace(mark, ".")
        try:
            return float(token)
        except ValueError:
            self.index = start
            return None


def _match_name(cursor: _Cursor, names: list[str]) -> int | None:
    rest = cursor.text[cursor.index:].lower()
    best = None
    for index, name in enumerate(names):
        lowered = name.lower()
        if lowered and rest.startswith(lowered):
            if best is None or len(lowered) > len(best[1]):
                best = (index, lowered)
    if best is None:
        return None
    cursor.index += len(best[1])
    return best[0] + 1


def _parse_date(cursor: _Cursor) -> bool:
    year = cursor.integer(4, exact=True)
    if year is None:
        return False
    if not cursor.take_this("-") and not cursor.take_this("/"):
        return False
    month = cursor.integer(2, exact=True)
    if month is None:
        return False
    if not cursor.take_this("-") and not cursor.take_this("/"):
        return False
    day = cursor.integer(2, exact=True)
    if day is None:
        return False
    cursor.year, cursor.mon, cursor.day = year, month, day
    return True


def _parse_time(cursor: _Cursor) -> bool:
    hour = cursor.integer(2, exact=False)
    if hour is None or not cursor.take_this(":"):
        return False
    minute = cursor.integer(2, exact=True)
    if minute is None:
        return False
    cursor.take_this(":")
    seconds = cursor.number()
    if seconds is not None:
        cursor.second = int(seconds)
    cursor.hour = hour
    cursor.minute = minute
    cursor.skip_space()
    am_pm = _match_name(cursor, list(cursor.loc.date_names.am_pm))
    if am_pm is not None:
        cursor.am_pm = am_pm
    cursor.skip_space()
    return cursor.done()


def _parse_iso(cursor: _Cursor) -> bool:
    year = cursor.integer(4, exact=True)
    if year is None:
        return False
    cursor.year = year
    if cursor.take_this("-"):
        cursor.compact = False
    month = cursor.integer(2, exact=True)
    if month is None:
        return False
    cursor.mon = month
    if not cursor.compact and not cursor.take_this("-"):
        return False
    day = cursor.integer(2, exact=True)
    if day is None:
        return False
    cursor.day = day
    if cursor.done():
        return True
    separator = cursor.take()
    if separator not in "T ":
        return False
    hour = cursor.integer(2, exact=True)
    if hour is None:
        return False
    cursor.hour = hour
    cursor.take_this(":")
    minute = cursor.integer(2, exact=True)
    if minute is not None:
        cursor.minute = minute
    cursor.take_this(":")
    seconds = cursor.number()
    if seconds is not None:
        cursor.second = int(seconds)
        cursor.psec = seconds - cursor.second
    if cursor.done():
        return True
    cursor.tz = "UTC"
    if cursor.take_this("Z"):
        return cursor.done()
    sign = 1
    if cursor.peek() in "+-":
        sign = -1 if cursor.take() == "-" else 1
    hours = cursor.integer(2, exact=True)
    if hours is None:
        return False
    cursor.take_this(":")
    minutes = cursor.integer(2, exact=True) or 0
    cursor.offset_hours = sign * hours
    cursor.offset_minutes = sign * minutes
    return cursor.done()


def _apply_format(cursor: _Cursor, fmt: str) -> bool:
    cursor.skip_space()
    index = 0
    while index < len(fmt):
        character = fmt[index]
        if character.isspace():
            cursor.skip_space()
            index += 1
            continue
        if character != "%":
            if not cursor.take_this(character):
                return False
            index += 1
            continue
        index += 1
        if index >= len(fmt):
            raise ValueError("Invalid format: trailing %")
        code = fmt[index]
        index += 1
        if code == "Y":
            value = cursor.integer(4, exact=True)
            if value is None:
                return False
            cursor.year = value
        elif code == "y":
            value = cursor.integer(2, exact=True)
            if value is None:
                return False
            cursor.year = value + (2000 if value < 69 else 1900)
        elif code == "m":
            value = cursor.integer(2, exact=False)
            if value is None:
                return False
            cursor.mon = value
        elif code == "d":
            value = cursor.integer(2, exact=False)
            if value is None:
                return False
            cursor.day = value
        elif code == "b":
            value = _match_name(cursor, list(cursor.loc.date_names.mon_ab))
            if value is None:
                return False
            cursor.mon = value
        elif code == "B":
            value = _match_name(cursor, list(cursor.loc.date_names.mon))
            if value is None:
                return False
            cursor.mon = value
        elif code == "H":
            value = cursor.integer(2, exact=False)
            if value is None or not 0 <= value <= 23:
                return False
            cursor.hour = value
        elif code == "M":
            value = cursor.integer(2, exact=True)
            if value is None:
                return False
            cursor.minute = value
        elif code == "S":
            seconds = cursor.number()
            if seconds is None:
                return False
            cursor.second = int(seconds)
        elif code == "O":
            if index >= len(fmt) or fmt[index] != "S":
                raise ValueError("Invalid format: %O must be followed by %S")
            index += 1
            seconds = cursor.number()
            if seconds is None:
                return False
            cursor.second = int(seconds)
            cursor.psec = seconds - cursor.second
        elif code == "p":
            value = _match_name(cursor, list(cursor.loc.date_names.am_pm))
            if value is None:
                return False
            cursor.am_pm = value
        elif code == "A":
            if index >= len(fmt):
                raise ValueError("Invalid format: %A must be followed by another letter")
            which = fmt[index]
            index += 1
            if which == "D":
                if not _parse_date(cursor):
                    return False
            elif which == "T":
                if not _parse_time(cursor):
                    return False
            else:
                raise ValueError("Invalid %A auto parser")
        elif code == "F":
            if not _apply_format(cursor, "%Y-%m-%d"):
                return False
        elif code == "D":
            if not _apply_format(cursor, "%m/%d/%y"):
                return False
        elif code == "R":
            if not _apply_format(cursor, "%H:%M"):
                return False
        elif code in ("X", "T"):
            if not _apply_format(cursor, "%H:%M:%S"):
                return False
        elif code == "z":
            cursor.tz = "UTC"
            if cursor.take_this("Z"):
                continue
            sign = 1
            if cursor.peek() in "+-":
                sign = -1 if cursor.take() == "-" else 1
            hours = cursor.integer(2, exact=True)
            if hours is None:
                return False
            cursor.take_this(":")
            minutes = cursor.integer(2, exact=True) or 0
            cursor.offset_hours = sign * hours
            cursor.offset_minutes = sign * minutes
        elif code == "Z":
            start = cursor.index
            while not cursor.done() and not cursor.peek().isspace():
                cursor.index += 1
            if cursor.index == start:
                return False
            cursor.tz = cursor.text[start:cursor.index]
        else:
            raise ValueError(f"Unsupported format %{code}")
    cursor.skip_space()
    return cursor.done()


def _clock_hour(cursor: _Cursor) -> int:
    hour = cursor.hour
    if hour == 12:
        return 0 if cursor.am_pm == 1 else hour
    if cursor.am_pm == 2:
        return hour + 12
    return hour


def _valid_date(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _zone(name: str):
    if name in ("UTC", "GMT", "Etc/UTC", "Etc/GMT"):
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def _make_datetime(cursor: _Cursor) -> datetime | None:
    if not _valid_date(cursor.year, cursor.mon, cursor.day):
        return None
    hour = _clock_hour(cursor)
    second = cursor.second
    extra = cursor.psec
    aware = datetime(
        cursor.year,
        cursor.mon,
        cursor.day,
        hour,
        cursor.minute,
        second,
        int(round(extra * 1_000_000)),
        tzinfo=_zone(cursor.tz),
    )
    if cursor.tz == "UTC" and (cursor.offset_hours or cursor.offset_minutes):
        aware = aware - timedelta(
            hours=cursor.offset_hours, minutes=cursor.offset_minutes
        )
        aware = aware.astimezone(timezone.utc)
    return aware


def parse_date_text(text: str, loc: Locale, fmt: str) -> date | None:
    cursor = _Cursor(text, loc)
    if fmt:
        ok = _apply_format(cursor, fmt)
    else:
        cursor.skip_space()
        ok = _parse_date(cursor)
        cursor.skip_space()
        ok = ok and cursor.done()
    if not ok or not _valid_date(cursor.year, cursor.mon, cursor.day):
        return None
    return date(cursor.year, cursor.mon, cursor.day)


def parse_time_text(text: str, loc: Locale, fmt: str) -> Hms | None:
    cursor = _Cursor(text, loc)
    if fmt:
        ok = _apply_format(cursor, fmt)
    else:
        cursor.skip_space()
        ok = _parse_time(cursor)
    if not ok:
        return None
    seconds = cursor.sign * (
        _clock_hour(cursor) * 3600 + cursor.minute * 60 + cursor.second + cursor.psec
    )
    return Hms(seconds)


def parse_datetime_text(text: str, loc: Locale, fmt: str) -> datetime | None:
    cursor = _Cursor(text, loc)
    if fmt:
        ok = _apply_format(cursor, fmt)
    else:
        ok = _parse_iso(cursor)
    if not ok:
        return None
    return _make_datetime(cursor)


def _parse_double(text: str, mark: str) -> float | None:
    if not text:
        return None
    if mark != ".":
        if text.count(mark) > 1:
            return None
        text = text.replace(mark, ".")
    try:
        value = float(text)
    except ValueError:
        return None
    if math.isfinite(value) or math.isnan(value) or math.isinf(value):
        lowered = text.lower().lstrip("+-")
        if lowered in ("nan", "inf", "infinity"):
            return value
        cleaned = text.lower().replace(".", "").replace("+", "").replace("-", "")
        cleaned = cleaned.replace("e", "")
        if cleaned and not cleaned.isdigit():
            return None
        return value
    return None


def _leading_zero(text: str, mark: str) -> bool:
    return len(text) > 1 and text[0] == "0" and text[1] != mark


def _parse_integer(text: str) -> int | None:
    if not text:
        return None
    body = text[1:] if text[0] in "+-" else text
    if not body.isdigit():
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    if value < _INT_MIN or value > _INT_MAX:
        return None
    return value


def _parse_number(text: str, loc: Locale, strict: bool) -> float | None:
    mark = loc.decimal_mark
    group = loc.grouping_mark
    start = 0
    while start < len(text):
        character = text[start]
        if character == "-" or character == mark or character.isdigit():
            break
        start += 1
    if start == len(text):
        return None
    if strict and start != 0:
        return None
    index = start
    sign = 1.0
    if text[index] == "-":
        sign = -1.0
        index += 1
    saw = False
    left = True
    total = 0.0
    denom = 1.0
    exponent = 0.0
    exp_sign = 1.0
    exp_init = True
    while index < len(text):
        if group and text.startswith(group, index):
            index += len(group)
            continue
        character = text[index]
        if left and character == mark:
            left = False
            index += 1
            continue
        if saw and character in "eE":
            index += 1
            left = False
            while index < len(text):
                exp_char = text[index]
                if exp_init and exp_char == "-":
                    exp_sign = -1.0
                    exp_init = False
                    index += 1
                    continue
                if exp_init and exp_char == "+":
                    exp_init = False
                    index += 1
                    continue
                if exp_char.isdigit():
                    exponent = exponent * 10 + int(exp_char)
                    exp_init = False
                    index += 1
                    continue
                break
            break
        if character.isdigit():
            saw = True
            if left:
                total = total * 10 + int(character)
            else:
                denom *= 10
                total += int(character) / denom
            index += 1
            continue
        break
    if strict and index != len(text):
        return None
    if not saw:
        return None
    value = sign * total
    if exponent:
        value *= 10 ** (exp_sign * exponent)
    return value


def _is_missing(text: str, na) -> bool:
    return text in na


def guess_type(values, na=("","NA"), loc=None, guess_integer=False) -> str:
    """The type vroom would guess. Whole numbers are doubles unless asked."""
    loc = loc or default_locale()
    if len(values) == 0:
        return "character"
    prepared = []
    for value in values:
        if value is None:
            prepared.append(None)
            continue
        text = value if isinstance(value, str) else str(value)
        prepared.append(None if _is_missing(text, na) or text == "" else text)
    if all(value is None for value in prepared):
        return "logical"

    def ok(predicate) -> bool:
        return all(value is None or predicate(value) for value in prepared)

    if ok(lambda text: text in _TRUE or text in _FALSE):
        return "logical"
    if guess_integer and ok(lambda text: not _leading_zero(text, ".") and _parse_integer(text) is not None and (len(text) == 1 or text[0] != "0")):
        return "integer"
    if ok(lambda text: not _leading_zero(text, loc.decimal_mark) and _parse_double(text, loc.decimal_mark) is not None):
        return "double"
    if ok(lambda text: not (len(text) > 1 and text[0] == "0" and text[1] != loc.decimal_mark) and _parse_number(text, loc, True) is not None):
        return "number"
    if ok(lambda text: parse_time_text(text, loc, "") is not None):
        return "time"
    if ok(lambda text: parse_date_text(text, loc, "") is not None):
        return "date"
    if ok(lambda text: _datetime_guess(text, loc)):
        return "datetime"
    return "character"


def _datetime_guess(text: str, loc=None) -> bool:
    loc = loc or default_locale()
    cursor = _Cursor(text, loc)
    if not _parse_iso(cursor):
        return False
    if cursor.compact and cursor.year <= 999:
        return False
    return _make_datetime(cursor) is not None


def parse_one(text, collector: Collector, loc: Locale, na, trim_ws: bool, quoted: bool = False, quoted_na: bool = True):
    """Parse one field. Returns (value, failure expected-string or None)."""
    if text is None:
        return None, None
    original = text
    if trim_ws:
        text = text.strip(" \t")
    if text == "" or (text in na and (quoted_na or not quoted)):
        return None, None
    kind = collector.kind
    if kind == "skip":
        return None, None
    if kind == "character":
        return text, None
    if kind == "logical":
        if text in _TRUE or text == "1":
            return True, None
        if text in _FALSE or text == "0":
            return False, None
        return None, "1/0/T/F/TRUE/FALSE"
    if kind == "integer":
        value = _parse_integer(text)
        if value is None:
            return None, "an integer"
        return value, None
    if kind == "double":
        value = _parse_double(text, loc.decimal_mark)
        if value is None:
            return None, "a double"
        return value, None
    if kind == "number":
        value = _parse_number(text, loc, False)
        if value is None:
            return None, "a number"
        return value, None
    if kind == "date":
        fmt = collector.fields.get("format") or ""
        value = parse_date_text(text, loc, fmt)
        if value is None:
            expected = "date in ISO8601" if not fmt else f"date like {fmt}"
            return None, expected
        return value, None
    if kind == "time":
        fmt = collector.fields.get("format") or ""
        value = parse_time_text(text, loc, fmt)
        if value is None:
            expected = "time in ISO8601" if not fmt else f"time like {fmt}"
            return None, expected
        return value, None
    if kind == "datetime":
        fmt = collector.fields.get("format") or ""
        value = parse_datetime_text(text, loc, fmt)
        if value is None:
            expected = "date in ISO8601" if not fmt else f"date like {fmt}"
            return None, expected
        return value, None
    if kind == "factor":
        levels = collector.fields.get("levels")
        if levels is None:
            return text, None
        if text in levels:
            return text, None
        return None, "value in level set"
    if kind == "guess":
        guessed = collector_for_name(guess_type([text], na, loc))
        return parse_one(original, guessed, loc, na, trim_ws, quoted, quoted_na)
    return text, None


def parse_vector(values, collector, na=("", "NA"), locale=None, trim_ws=True, style="parse"):
    """Parse a character vector and attach problems to the result list."""
    loc = locale or default_locale()
    if isinstance(collector, str):
        collector = collector_for_name(collector) if len(collector) > 1 else __import__(
            "readr.columns", fromlist=["col_concise"]
        ).col_concise(collector)
    problems = []
    parsed = []
    pending_levels = collector.kind == "factor" and collector.fields.get("levels") is None
    for index, value in enumerate(values, start=1):
        if value is None:
            text = None
        else:
            text = value if isinstance(value, str) else str(value)
        result, expected = parse_one(text, collector, loc, tuple(na), trim_ws)
        if style == "parse" and collector.kind == "date" and expected == "date in ISO8601":
            # parse_date distinguishes a formatted date that is not a real day
            if text and parse_date_loose(text, loc):
                expected = "valid date"
            elif text:
                expected = "date like " + (collector.fields.get("format") or "")
        parsed.append(result)
        if expected is not None:
            problems.append(
                {"row": index, "col": None, "expected": expected, "actual": text, "file": ""}
            )
    if pending_levels:
        include_na = collector.fields.get("include_na", False)
        levels = []
        for value in parsed:
            if value is None:
                continue
            if value not in levels:
                levels.append(value)
        if include_na:
            levels.append(None)
        parsed = Factor(parsed, levels, collector.fields.get("ordered", False))
    elif collector.kind == "factor":
        parsed = Factor(parsed, list(collector.fields.get("levels") or []), collector.fields.get("ordered", False))
    parsed = _Parsed(parsed, problems, collector.kind)
    if problems and style == "parse":
        _warn_parse(problems)
    return parsed


def parse_date_loose(text: str, loc: Locale) -> bool:
    cursor = _Cursor(text, loc)
    cursor.skip_space()
    ok = _parse_date(cursor)
    cursor.skip_space()
    return ok and cursor.done()


class _Parsed(list):
    def __init__(self, values, problems, kind):
        if isinstance(values, Factor):
            super().__init__(values.values)
            self.factor = values
        else:
            super().__init__(values)
            self.factor = None
        self.problems = problems
        self.kind = kind


def _warn_parse(problems) -> None:
    count = len(problems)
    noun = "parsing failure" if count == 1 else "parsing failures"
    lines = [f"{count} {noun}.", "row col expected actual"]
    for problem in problems[:5]:
        column = "--" if problem["col"] is None else str(problem["col"])
        lines.append(
            f"{problem['row']} {column} {problem['expected']} {problem['actual']}"
        )
    warnings.warn("\n".join(lines), stacklevel=3)


def parse_logical(x, na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_logical

    return parse_vector(x, col_logical(), na, locale, trim_ws)


def parse_integer(x, na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_integer

    return parse_vector(x, col_integer(), na, locale, trim_ws)


def parse_double(x, na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_double

    return parse_vector(x, col_double(), na, locale, trim_ws)


def parse_character(x, na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_character

    return parse_vector(x, col_character(), na, locale, trim_ws)


def parse_number(x, na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_number

    return parse_vector(x, col_number(), na, locale, trim_ws)


def parse_date(x, format="", na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_date

    return parse_vector(x, col_date(format), na, locale, trim_ws)


def parse_datetime(x, format="", na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_datetime

    return parse_vector(x, col_datetime(format), na, locale, trim_ws)


def parse_time(x, format="", na=("", "NA"), locale=None, trim_ws=True):
    from readr.columns import col_time

    return parse_vector(x, col_time(format), na, locale, trim_ws)


def parse_factor(x, levels=None, ordered=False, na=("", "NA"), locale=None, trim_ws=True, include_na=False):
    from readr.columns import col_factor

    return parse_vector(x, col_factor(levels, ordered, include_na), na, locale, trim_ws)


def guess_parser(x, locale=None, na=("", "NA"), guess_integer=False):
    """The type name guess_parser would return for a character vector."""
    loc = locale or default_locale()
    return guess_type(list(x), na, loc, guess_integer)


def parse_guess(x, na=("", "NA"), locale=None, trim_ws=True, guess_integer=False):
    kind = guess_parser(x, locale, na, guess_integer)
    return parse_vector(x, collector_for_name(kind), na, locale, trim_ws)
