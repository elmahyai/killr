"""A time interval stored in seconds, including R's missing values."""

import math


class Difftime:
    """R `difftime` after `units<-` has converted the values to seconds.

    `None` is R's NA. `float("nan")` is NaN. A scalar is stored as a
    one-element list.
    """

    _SCALES = {
        "secs": 1.0,
        "mins": 60.0,
        "hours": 3600.0,
        "days": 86400.0,
        "weeks": 604800.0,
    }

    def __init__(self, values, units="secs"):
        if units not in self._SCALES:
            raise ValueError(f"unknown units {units!r}")
        if isinstance(values, bool) or (
            not isinstance(values, (list, tuple))
            and not _is_real(values)
            and values is not None
        ):
            raise TypeError("difftime values must be numeric")
        if _is_real(values) or values is None:
            values = [values]
        scale = self._SCALES[units]
        seconds = []
        for value in values:
            if isinstance(value, bool) or (value is not None and not _is_real(value)):
                raise TypeError("difftime values must be numeric")
            if value is None:
                seconds.append(None)
            else:
                number = float(value)
                seconds.append(number * scale if not math.isnan(number) else number)
        self.seconds = seconds

    def __len__(self):
        return len(self.seconds)


def _is_real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
