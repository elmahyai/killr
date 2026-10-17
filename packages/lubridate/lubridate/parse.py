"""Order-based date parsers.

A string is split into numbers. Those numbers fill the letters of an order
such as ``ymd`` or ``ymdHMS``. A two-digit year from 00 to 68 is 2000 to
2068. A missing trailing field allowed by ``truncated`` is 1 for a date
part and 0 for a time part.
"""

import math
import re

import numpy as np

from timechange import time_update
from timechange.civil import Posixct

from .instants import Date, _as_instant
from .spans import Period

_ORDERS = {
    "ymd": "ymd", "ydm": "ydm", "mdy": "mdy", "myd": "myd", "dmy": "dmy", "dym": "dym",
    "yq": "yq", "ym": "ym", "my": "my",
    "ymd_hms": "ymdHMS", "ymd_hm": "ymdHM", "ymd_h": "ymdH",
    "dmy_hms": "dmyHMS", "dmy_hm": "dmyHM", "dmy_h": "dmyH",
    "mdy_hms": "mdyHMS", "mdy_hm": "mdyHM", "mdy_h": "mdyH",
    "ydm_hms": "ydmHMS", "ydm_hm": "ydmHM", "ydm_h": "ydmH",
}


def _numbers(text, decimal=False):
    raw = str(text) if decimal else str(text).replace(".", " ")
    return [float(piece) for piece in re.findall(r"\d+\.?\d*|\.\d+", raw)]


def _year(value):
    if value >= 100:
        return int(value)
    if value <= 68:
        return int(value) + 2000
    return int(value) + 1900


def _parse_one(text, order, truncated):
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return None
    raw = str(text).strip()
    if raw == "" or raw.lower() == "na":
        return None
    nums = _numbers(raw, decimal=("S" in order))
    if len(nums) == 1 and order.startswith("ymd"):
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 8 and order == "ymd":
            nums = [float(digits[:4]), float(digits[4:6]), float(digits[6:])]
        elif len(digits) >= 14 and "H" in order:
            nums = [float(digits[:4]), float(digits[4:6]), float(digits[6:8]),
                    float(digits[8:10]), float(digits[10:12]), float(digits[12:14])]
    letters = [{"Y": "y"}.get(item, item) for item in order]
    if len(nums) < len(letters) - truncated or len(nums) == 0:
        return None
    if len(nums) < len(letters):
        letters = letters[:len(nums)]
    fields = {"y": 1970, "m": 1, "d": 1, "q": None, "H": 0, "M": 0, "S": 0.0}
    for letter, value in zip(letters, nums):
        fields[letter] = value
    if fields["q"] is not None:
        fields["m"] = int((fields["q"] - 1) * 3 + 1)
        fields["d"] = 1
    try:
        return (
            _year(fields["y"]), int(fields["m"]), int(fields["d"]),
            int(fields["H"]), int(fields["M"]), float(fields["S"]),
        )
    except (ValueError, OverflowError):
        return None


def _to_posix(rows, tz):
    if not rows:
        return Posixct([], tz or "UTC")
    year, month, day, hour, minute, second = zip(*rows)
    base = Posixct(np.zeros(len(rows)), "UTC")
    return time_update(
        base, year=list(year), month=list(month), mday=list(day),
        hour=list(hour), minute=list(minute), second=list(second),
        tz=tz or "UTC", roll_month="full", roll_dst=("boundary", "post"),
    )


def parse_date_time(x, orders, tz="UTC", truncated=0, quiet=False, exact=False):
    texts = np.atleast_1d(np.asarray(x, dtype=object))
    order_list = [orders] if isinstance(orders, str) else list(orders)
    order_list = [_ORDERS.get(item, item) for item in order_list]
    rows = []
    for text in texts.reshape(-1):
        parsed = None
        for order in order_list:
            parsed = _parse_one(text, order, truncated)
            if parsed is not None:
                break
        rows.append(parsed if parsed is not None else (np.nan, 1, 1, 0, 0, 0))
    built = []
    for row in rows:
        if isinstance(row[0], float) and math.isnan(row[0]):
            built.append(np.nan)
        else:
            built.append(row)
    good = [row if not (isinstance(row[0], float) and math.isnan(row[0])) else (1970, 1, 1, 0, 0, 0) for row in rows]
    result = _to_posix(good, tz)
    seconds = np.array(result.seconds, dtype=float, copy=True)
    for i, row in enumerate(rows):
        if isinstance(row[0], float) and math.isnan(row[0]):
            seconds.reshape(-1)[i] = np.nan
    return Posixct(seconds.reshape(result.seconds.shape), result.tz)


parse_date_time2 = parse_date_time


def _family(order, texts, quiet, tz, truncated, as_date=False):
    parsed = parse_date_time(np.atleast_1d(np.asarray(texts, dtype=object)), order, tz or "UTC", truncated, quiet)
    if as_date:
        from .instants import date
        return date(parsed)
    return parsed


def ymd(*texts, quiet=False, tz=None, locale=None, truncated=0):
    return _family("ymd", _flatten(texts), quiet, tz, truncated, as_date=tz is None)


def ydm(*texts, quiet=False, tz=None, locale=None, truncated=0):
    return _family("ydm", _flatten(texts), quiet, tz, truncated, as_date=tz is None)


def mdy(*texts, quiet=False, tz=None, locale=None, truncated=0):
    return _family("mdy", _flatten(texts), quiet, tz, truncated, as_date=tz is None)


def myd(*texts, quiet=False, tz=None, locale=None, truncated=0):
    return _family("myd", _flatten(texts), quiet, tz, truncated, as_date=tz is None)


def dmy(*texts, quiet=False, tz=None, locale=None, truncated=0):
    return _family("dmy", _flatten(texts), quiet, tz, truncated, as_date=tz is None)


def dym(*texts, quiet=False, tz=None, locale=None, truncated=0):
    return _family("dym", _flatten(texts), quiet, tz, truncated, as_date=tz is None)


def yq(*texts, quiet=False, tz=None, locale=None):
    return _family("yq", _flatten(texts), quiet, tz, 0, as_date=tz is None)


def ym(*texts, quiet=False, tz=None, locale=None):
    return _family("ym", _flatten(texts), quiet, tz, 0, as_date=tz is None)


def my(*texts, quiet=False, tz=None, locale=None):
    return _family("my", _flatten(texts), quiet, tz, 0, as_date=tz is None)


def ymd_hms(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("ymdHMS", _flatten(texts), quiet, tz, truncated)


def ymd_hm(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("ymdHM", _flatten(texts), quiet, tz, truncated)


def ymd_h(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("ymdH", _flatten(texts), quiet, tz, truncated)


def dmy_hms(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("dmyHMS", _flatten(texts), quiet, tz, truncated)


def dmy_hm(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("dmyHM", _flatten(texts), quiet, tz, truncated)


def dmy_h(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("dmyH", _flatten(texts), quiet, tz, truncated)


def mdy_hms(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("mdyHMS", _flatten(texts), quiet, tz, truncated)


def mdy_hm(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("mdyHM", _flatten(texts), quiet, tz, truncated)


def mdy_h(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("mdyH", _flatten(texts), quiet, tz, truncated)


def ydm_hms(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("ydmHMS", _flatten(texts), quiet, tz, truncated)


def ydm_hm(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("ydmHM", _flatten(texts), quiet, tz, truncated)


def ydm_h(*texts, quiet=False, tz="UTC", locale=None, truncated=0):
    return _family("ydmH", _flatten(texts), quiet, tz, truncated)


def _flatten(texts):
    out = []
    for item in texts:
        if isinstance(item, (list, tuple, np.ndarray)):
            out.extend(list(np.atleast_1d(item)))
        else:
            out.append(item)
    return out


def hms(*texts, quiet=False, roll=False):
    return _hms_order(_flatten(texts), "HMS", roll)


def hm(*texts, quiet=False, roll=False):
    return _hms_order(_flatten(texts), "HM", roll)


def ms(*texts, quiet=False, roll=False):
    return _hms_order(_flatten(texts), "MS", roll)


def _hms_order(texts, order, roll):
    hours, minutes, seconds = [], [], []
    for text in texts:
        nums = _numbers(text, decimal=("S" in order))
        letters = list(order)
        fields = {"H": 0.0, "M": 0.0, "S": 0.0}
        for letter, value in zip(letters, nums):
            fields[letter] = value
        hour, minute, second = fields["H"], fields["M"], fields["S"]
        if roll:
            minute += second // 60
            second = second % 60
            hour += minute // 60
            minute = minute % 60
        hours.append(hour)
        minutes.append(minute)
        seconds.append(second)
    return Period(seconds, minutes, hours, 0, 0, 0)


def fast_strptime(x, format, tz="UTC", lt=False, cutoff_2000=68):
    mapping = {
        "%Y": r"(\d{4})", "%y": r"(\d{2})", "%m": r"(\d{1,2})", "%d": r"(\d{1,2})",
        "%H": r"(\d{1,2})", "%M": r"(\d{1,2})", "%S": r"(\d{1,2})", "%OS": r"(\d+\.?\d*)",
    }
    pattern = re.escape(format)
    letters = []
    for token, group in mapping.items():
        if token in format:
            letters.append(token)
            pattern = pattern.replace(re.escape(token), group)
    rows = []
    for text in np.atleast_1d(np.asarray(x, dtype=object)).reshape(-1):
        found = re.fullmatch(pattern, str(text).strip())
        if not found:
            rows.append(None)
            continue
        fields = {"%Y": 1970, "%y": None, "%m": 1, "%d": 1, "%H": 0, "%M": 0, "%S": 0, "%OS": 0}
        for letter, value in zip(letters, found.groups()):
            fields[letter] = float(value)
        year = int(fields["%Y"])
        if fields["%y"] is not None:
            year = int(fields["%y"]) + (2000 if fields["%y"] <= cutoff_2000 else 1900)
        rows.append((year, int(fields["%m"]), int(fields["%d"]), int(fields["%H"]), int(fields["%M"]), float(fields["%OS"] or fields["%S"])))
    good = [row or (1970, 1, 1, 0, 0, 0) for row in rows]
    result = _to_posix(good, tz)
    seconds = np.array(result.seconds, dtype=float, copy=True)
    for i, row in enumerate(rows):
        if row is None:
            seconds.reshape(-1)[i] = np.nan
    return Posixct(seconds, result.tz)


def guess_formats(x, orders, locale=None):
    """Return the strptime orders that match, with ``%Om`` tried before ``%m``."""
    import re
    requested = [orders] if isinstance(orders, str) else list(orders)
    texts = [str(item) for item in np.atleast_1d(np.asarray(x, dtype=object)).reshape(-1)]
    found = []
    letter = {"y": "%Y", "Y": "%Y", "m": "%m", "d": "%d", "H": "%H", "M": "%M", "S": "%S"}
    for order in requested:
        clean = re.sub(r"[^A-Za-z]+", "", order)
        for text in texts:
            seps = re.findall(r"\D+", text)
            nums = re.findall(r"\d+", text)
            if len(nums) < len(clean):
                continue
            body = []
            for i, item in enumerate(clean):
                token = "%Om" if item == "m" else letter.get(item, "%" + item)
                body.append(token)
                if i < len(seps):
                    body.append(seps[i])
            om = "".join(body)
            plain = om.replace("%Om", "%m")
            for fmt in ((om, plain) if "%Om" in om else (plain,)):
                if fmt not in found:
                    found.append(fmt)
    return np.array(found, dtype=object)
