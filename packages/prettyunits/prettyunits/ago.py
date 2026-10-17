"""Human readable ages, from prettyunits `vague_dt` and `time_ago`."""

import math
from datetime import datetime

from prettyunits._difftime import Difftime
from prettyunits._r import match_arg, r_round

_FORMATS = ("default", "short", "terse")


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _below(name, limit):
    def condition(pieces):
        value = pieces[name]
        if _missing(value):
            raise ValueError("missing value where TRUE/FALSE needed")
        return value < limit

    return condition


def _always(_pieces):
    return True


def _fixed(text):
    def render(_pieces):
        return text

    return render


def _sprintf_d(template, value):
    """R `sprintf` with `%d` or `%2d`. The number is an integer, space padded."""
    rounded = r_round(value)
    if _missing(rounded) or math.isinf(rounded):
        spec = "%2d" if "%2d" in template else "%d"
        raise ValueError(
            f"invalid format '{spec}'; use format %f, %e, %g or %a for numeric objects"
        )
    return template % int(rounded)


def _counted(template, name, divisor=1.0):
    def render(pieces):
        return _sprintf_d(template, pieces[name] / divisor)

    return render


# The last row of each table is always true, as in the R source.
_DEFAULT = (
    (_below("seconds", 10), _fixed("moments ago")),
    (_below("seconds", 45), _fixed("less than a minute ago")),
    (_below("seconds", 90), _fixed("about a minute ago")),
    (_below("minutes", 45), _counted("%d minutes ago", "minutes")),
    (_below("minutes", 90), _fixed("about an hour ago")),
    (_below("hours", 24), _counted("%d hours ago", "hours")),
    (_below("hours", 42), _fixed("a day ago")),
    (_below("days", 30), _counted("%d days ago", "days")),
    (_below("days", 45), _fixed("about a month ago")),
    (_below("days", 335), _counted("%d months ago", "days", 30)),
    (_below("years", 1.5), _fixed("about a year ago")),
    (_always, _counted("%d years ago", "years")),
)

_SHORT = (
    (_below("seconds", 50), _fixed("<1 min")),
    (_below("minutes", 50), _counted("%d min", "minutes")),
    (_below("hours", 1.5), _fixed("1 hour")),
    (_below("hours", 18), _counted("%d hours", "hours")),
    (_below("hours", 42), _fixed("1 day")),
    (_below("days", 30), _counted("%d day", "days")),
    (_below("days", 45), _fixed("1 mon")),
    (_below("days", 335), _counted("%d mon", "days", 30)),
    (_below("years", 1.5), _fixed("1 year")),
    (_always, _counted("%d years", "years")),
)

_TERSE = (
    (_below("seconds", 50), _counted("%2ds", "seconds")),
    (_below("minutes", 50), _counted("%2dm", "minutes")),
    (_below("hours", 18), _counted("%2dh", "hours")),
    (_below("days", 30), _counted("%2dd", "days")),
    (_below("days", 335), _counted("%2dM", "days", 30)),
    (_always, _counted("%2dy", "years")),
)

_TABLES = {
    "default": _DEFAULT,
    "short": _SHORT,
    "terse": _TERSE,
}


def _pieces(seconds):
    return {
        "seconds": seconds,
        "minutes": seconds / 60,
        "hours": seconds / 60 / 60,
        "days": seconds / 60 / 60 / 24,
        "years": seconds / 60 / 60 / 24 / 365.25,
    }


def vague_dt(dt, format=_FORMATS):
    """Format one difftime in the default, short, or terse style.

    An empty interval returns []. A longer interval raises ValueError,
    because R 4.5 `if()` rejects a condition longer than one.
    """
    if not isinstance(dt, Difftime):
        raise ValueError("dt must be a difftime")
    values = dt.seconds
    if len(values) == 0:
        return []
    chosen = match_arg(format, _FORMATS)
    if len(values) > 1:
        raise ValueError("the condition has length > 1")
    seconds = values[0]
    if _missing(seconds):
        raise ValueError("missing value where TRUE/FALSE needed")
    pieces = _pieces(seconds)
    for condition, render in _TABLES[chosen]:
        if condition(pieces):
            return render(pieces)
    raise RuntimeError("vague_dt format table has no matching row")


def _datetimes(date):
    if isinstance(date, datetime):
        return [date]
    if isinstance(date, (list, tuple)):
        for item in date:
            if not isinstance(item, datetime):
                raise TypeError("date must be a datetime or a list of datetimes")
        return list(date)
    raise TypeError("date must be a datetime or a list of datetimes")


def time_ago(date, format=_FORMATS):
    """Format the age of a naive local datetime, or of each datetime in a list.

    A list calls this function once per timestamp, passing `format` through.
    The default choice vector still selects "default" inside `vague_dt`.
    """
    dates = _datetimes(date)
    if len(dates) > 1:
        return [time_ago(item, format=format) for item in dates]
    if len(dates) == 0:
        return vague_dt(Difftime([], units="secs"), format=format)
    seconds = (datetime.now() - dates[0]).total_seconds()
    return vague_dt(Difftime(seconds, units="secs"), format=format)
