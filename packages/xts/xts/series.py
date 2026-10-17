"""An xts series: a matrix ordered by a numeric time index."""

from __future__ import annotations

from datetime import date, datetime, timezone

from xts.ordered import XtsError, isOrdered


class Xts:
    """Column-major data with a numeric index, in seconds since the epoch."""

    def __init__(self, columns, index, tzone="UTC", tclass=None, tformat=None, colnames=None, attrs=None):
        self.columns = [list(column) for column in columns]
        self.index = [float(value) for value in index]
        self.tzone = tzone if tzone is not None else ""
        self.tclass = list(tclass or ["POSIXct", "POSIXt"])
        self.tformat = tformat
        self.colnames = list(colnames) if colnames else None
        self.attrs = dict(attrs or {})
        self.class_attr = None

    def __len__(self) -> int:
        if not self.columns:
            return 0
        return len(self.columns[0])

    @property
    def nrow(self) -> int:
        return len(self)

    @property
    def ncol(self) -> int:
        return len(self.columns)

    def flat(self) -> list:
        values = []
        for column in self.columns:
            values.extend(column)
        return values

    def take(self, rows) -> "Xts":
        chosen = list(rows)
        columns = [[column[row] for row in chosen] for column in self.columns] or [[]]
        if columns == [[]] and chosen:
            columns = [[]]
        index = [self.index[row] for row in chosen]
        return Xts(columns if self.columns else [[]], index, self.tzone, self.tclass, self.tformat, self.colnames, self.attrs)

    def copy(self) -> "Xts":
        return self.take(range(self.nrow))


def _as_columns(x, nrow: int):
    if x is None:
        return [[]]
    if isinstance(x, Xts):
        return [list(column) for column in x.columns]
    if isinstance(x, (str, bytes)):
        raise XtsError("order.by requires an appropriate time-based object")
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], (list, tuple)):
        return [list(column) for column in x]
    if nrow == 0 and not isinstance(x, (list, tuple)):
        return [[]]
    return [list(x)]


def _stamp_of(value) -> float:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.timestamp()
        return value.timestamp()
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).timestamp()
    if isinstance(value, bool):
        raise XtsError("order.by requires an appropriate time-based object")
    if isinstance(value, (int, float)):
        raise XtsError("order.by requires an appropriate time-based object")
    raise XtsError("order.by requires an appropriate time-based object")


def _time_class(value) -> list[str]:
    if isinstance(value, datetime):
        return ["POSIXct", "POSIXt"]
    if isinstance(value, date):
        return ["Date"]
    return ["POSIXct", "POSIXt"]


def _zone_of(value, fallback: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return fallback
        name = getattr(value.tzinfo, "key", None) or ""
        if value.tzinfo == timezone.utc or name in {"UTC", "GMT"}:
            return "UTC"
        return name or fallback
    if isinstance(value, date):
        return "UTC"
    return fallback


def xts(x=None, order_by=None, frequency=None, unique=True, tzone=None, tclass=None, tformat=None, colnames=None, **attrs):
    """Build an xts series. ``order_by`` is a Date or POSIXct index."""
    del frequency
    if x is None and order_by is None:
        return dot_xts(None, [])
    if order_by is None:
        raise XtsError("order.by requires an appropriate time-based object")
    if isinstance(order_by, (datetime, date)):
        order_by = [order_by]
    stamps = [_stamp_of(value) for value in order_by]
    if not isOrdered(stamps, increasing=True, strictly=not unique):
        order = sorted(range(len(stamps)), key=stamps.__getitem__)
        stamps = [stamps[item] for item in order]
        if x is not None:
            columns = _as_columns(x, len(stamps))
            x = [[column[item] for item in order] for column in columns]
    columns = _as_columns(x, len(stamps))
    if columns and columns[0] and len(columns[0]) != len(stamps):
        raise XtsError("NROW(x) must match length(order.by)")
    if any(value != value or value in (float("inf"), float("-inf")) for value in stamps):
        raise XtsError("'order.by' cannot contain 'NA', 'NaN', or 'Inf'")
    sample = order_by[0]
    zone = tzone if tzone is not None else _zone_of(sample, "")
    klass = list(tclass) if tclass is not None else _time_class(sample)
    if klass == ["Date"]:
        zone = "UTC"
    if isinstance(zone, (list, tuple)):
        zone = zone[0]
    return Xts(columns, stamps, zone, klass, tformat, colnames, attrs)


def dot_xts(x=None, index=None, tclass=None, tzone="UTC", check=True, unique=False, tformat=None, colnames=None, **attrs):
    """Build an xts series from a numeric index, without sorting it."""
    if index is None:
        index = []
    stamps = [float(value) for value in index]
    if check and stamps and not isOrdered(stamps, increasing=True, strictly=unique):
        kind = "strictly " if unique else ""
        raise XtsError(f"index is not in {kind}increasing order")
    if any(value != value or value in (float("inf"), float("-inf")) for value in stamps):
        raise XtsError("'index' cannot contain 'NA', 'NaN', or 'Inf'")
    columns = _as_columns(x, len(stamps))
    if x is not None and columns and columns[0] and len(columns[0]) != len(stamps):
        raise XtsError("index length must match number of observations")
    klass = list(tclass) if tclass is not None else ["POSIXct", "POSIXt"]
    if isinstance(tzone, (list, tuple)):
        tzone = tzone[0]
    return Xts(columns, stamps, tzone if tzone is not None else "", klass, tformat, colnames, attrs)


def is_xts(x) -> bool:
    """True when ``x`` is an xts series with a numeric index and a tclass."""
    return isinstance(x, Xts) and x.tclass is not None and all(isinstance(value, float) for value in x.index)


def as_xts(x, order_by=None, **attrs):
    """Coerce a matrix, a Date, a POSIXct, or an xts series."""
    if isinstance(x, Xts):
        return x
    if isinstance(x, (datetime, date)) or (isinstance(x, (list, tuple)) and x and isinstance(x[0], (datetime, date))):
        return xts(None, x if not isinstance(x, (datetime, date)) else [x], **attrs)
    if order_by is None:
        raise XtsError("order.by is required")
    return xts(x, order_by, **attrs)


def xtsible(x) -> bool:
    """Whether ``as.xts`` can convert ``x``."""
    if isinstance(x, Xts):
        return True
    if isinstance(x, (datetime, date)):
        return True
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], (datetime, date)):
        return True
    return False


def index_get(x: Xts) -> list[float]:
    """The numeric index, in seconds since the epoch."""
    return list(x.index)


def index_set(x: Xts, value) -> Xts:
    """Replace the numeric index, keeping tclass and tzone."""
    out = x.copy()
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (datetime, date)):
        out.index = [_stamp_of(item) for item in value]
        out.tclass = _time_class(value[0])
        out.tzone = _zone_of(value[0], out.tzone)
        return out
    out.index = [float(item) for item in value]
    return out


def _component(x: Xts, which: str) -> list:
    rows = []
    zone = x.tzone or "UTC"
    for value in x.index:
        if zone in {"UTC", "GMT"}:
            stamp = datetime.fromtimestamp(value, timezone.utc)
        else:
            stamp = datetime.fromtimestamp(value)
        if which == "sec":
            rows.append(float(stamp.second + stamp.microsecond / 1_000_000))
        elif which == "min":
            rows.append(stamp.minute)
        elif which == "hour":
            rows.append(stamp.hour)
        elif which == "mday":
            rows.append(stamp.day)
        elif which == "mon":
            rows.append(stamp.month - 1)
        elif which == "year":
            rows.append(stamp.year - 1900)
        elif which == "wday":
            rows.append((stamp.weekday() + 1) % 7)
        elif which == "yday":
            rows.append(stamp.timetuple().tm_yday - 1)
        elif which == "isdst":
            flag = stamp.dst()
            rows.append(0 if not flag else 1)
        else:
            raise XtsError(which)
    return rows


def indexsec(x):
    return _component(x, "sec")


def indexmin(x):
    return _component(x, "min")


def indexhour(x):
    return _component(x, "hour")


def indexmday(x):
    return _component(x, "mday")


def indexmon(x):
    return _component(x, "mon")


def indexyear(x):
    return _component(x, "year")


def indexwday(x):
    return _component(x, "wday")


def indexyday(x):
    return _component(x, "yday")


def indexisdst(x):
    return _component(x, "isdst")


def indexDate(x):
    return [int(value // 86400) for value in x.index]


def indexday(x):
    return indexDate(x)


def indexweek(x):
    return [int((value + 3 * 86400) // 86400 // 7) for value in x.index]


def tzone(x: Xts) -> str:
    return x.tzone


def tzone_set(x: Xts, value: str) -> Xts:
    out = x.copy()
    out.tzone = value[0] if isinstance(value, (list, tuple)) else value
    return out


def tclass(x: Xts):
    return list(x.tclass)


def tclass_set(x: Xts, value) -> Xts:
    out = x.copy()
    klass = [value] if isinstance(value, str) else list(value)
    out.tclass = klass
    if klass and klass[0] == "Date":
        out.tzone = "UTC"
    return out


def tformat(x: Xts):
    return x.tformat


def tformat_set(x: Xts, value) -> Xts:
    out = x.copy()
    out.tformat = value
    return out


def indexTZ(x):
    return tzone(x)


def indexTZ_set(x, value):
    return tzone_set(x, value)


def indexClass(x):
    return tclass(x)


def indexClass_set(x, value):
    return tclass_set(x, value)


def indexFormat(x):
    return tformat(x)


def indexFormat_set(x, value):
    return tformat_set(x, value)


def convertIndex(x: Xts, value) -> Xts:
    return tclass_set(x, value)


def CLASS(x: Xts):
    return x.class_attr


def CLASS_set(x: Xts, value) -> Xts:
    out = x.copy()
    out.class_attr = value
    return out


def xtsAttributes(x: Xts):
    return dict(x.attrs) if x.attrs else None


def xtsAttributes_set(x: Xts, value) -> Xts:
    out = x.copy()
    out.attrs = dict(value or {})
    return out


def xcoredata(x: Xts) -> dict:
    """Attributes that coredata drops: the index, the class, and user attributes."""
    payload = {"index": list(x.index), "class": ["xts", "zoo"]}
    payload.update(x.attrs)
    return payload


def xcoredata_set(x: Xts, value) -> Xts:
    out = x.copy()
    out.attrs = {key: item for key, item in dict(value).items() if key not in {"index", "class"}}
    return out


def dimnames_xts(x: Xts):
    return [None, list(x.colnames) if x.colnames else None]


def dimnames_set(x: Xts, value) -> Xts:
    out = x.copy()
    if value and len(value) > 1 and value[1] is not None:
        names = value[1]
        out.colnames = [names] if isinstance(names, str) else list(names)
    else:
        out.colnames = None
    return out


def as_environment(x: Xts) -> dict:
    """Each column, under its name."""
    if not x.colnames:
        raise XtsError("invalid first argument")
    return {name: list(column) for name, column in zip(x.colnames, x.columns)}


def try_xts(x, error=True, **attrs):
    if isinstance(x, Xts):
        return x
    try:
        return as_xts(x, **attrs)
    except XtsError as exc:
        if error is True:
            raise
        if isinstance(error, str):
            raise XtsError(error) from exc
        return x


def use_xts(x, error=True, **attrs):
    return try_xts(x, error=error, **attrs)


def reclass(x, match_to=None, error=False):
    if match_to is not None and isinstance(match_to, Xts):
        if len(x) != match_to.nrow:
            if error:
                raise XtsError("incompatible match.to attibutes")
            return x
    return x


def use_reclass(x, match_to=None, error=False):
    return reclass(x, match_to, error)


def Reclass(x, match_to=None, error=False):
    return reclass(x, match_to, error)


def _row_positions(x: Xts, i) -> list[int]:
    if isinstance(i, str):
        from xts.iso import parse_iso8601

        parsed = parse_iso8601(i, tz=x.tzone or "")
        first = parsed["first.time"]
        last = parsed["last.time"]
        return [row for row, stamp in enumerate(x.index) if (first is None or stamp >= first) and (last is None or stamp <= last)]
    if isinstance(i, int):
        i = [i]
    return [int(item) - 1 for item in i]


def subset_xts(x: Xts, i=None, j=None):
    """``.subset.xts``, including an ISO-8601 string."""
    rows = range(x.nrow) if i is None else _row_positions(x, i)
    out = x.take(rows)
    if j is None:
        return out
    if isinstance(j, int):
        j = [j]
    chosen = [int(item) - 1 for item in j]
    out.columns = [out.columns[item] for item in chosen]
    if out.colnames:
        out.colnames = [out.colnames[item] for item in chosen]
    return out


def subset_xts_rows(x: Xts, i=None, j=None):
    """Integer row and column subset, 1-based, as ``.subset_xts``."""
    if isinstance(i, str):
        raise XtsError("i must be integer row positions")
    return subset_xts(x, i, j)
