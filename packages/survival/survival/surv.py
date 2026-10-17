"""The Surv response, from survival::Surv."""

import math
import warnings

import numpy as np

from survival.formatreal import format_real


def _as_float(values):
    if values is None:
        return None
    array = np.array(values, dtype=float)
    if array.ndim == 0:
        array = array.reshape(1)
    return array.reshape(-1)


def _is_factor(event):
    if event is None:
        return False
    if isinstance(event, (str, bytes)):
        return False
    try:
        sample = list(event)
    except TypeError:
        return False
    return bool(sample) and all(isinstance(item, str) for item in sample)


def _match_type(type):
    choices = ("right", "left", "interval", "counting", "interval2")
    if isinstance(type, (list, tuple)) and list(type) == list(choices):
        return choices[0]
    text = type[0] if isinstance(type, (list, tuple)) else type
    if text in choices:
        return text
    hits = [choice for choice in choices if choice.startswith(str(text))]
    if len(hits) == 1:
        return hits[0]
    raise ValueError("'type' should be one of " + ", ".join(repr(choice) for choice in choices))


class SurvObject:
    """A survival response. Columns are time and status, or start, stop, and status."""

    def __init__(self, columns, type, states=None, clabel=None):
        self.columns = np.array(columns, dtype=float, copy=True)
        if self.columns.ndim == 1:
            self.columns = self.columns.reshape(-1, 1)
        self.type = type
        self.states = None if states is None else list(states)
        self.clabel = clabel

    def __len__(self):
        return int(self.columns.shape[0])

    def __repr__(self):
        return " ".join(self.character())

    def character(self):
        kind = self.type
        columns = self.columns
        if kind == "right":
            status = columns[:, 1]
            suffix = np.where(np.isnan(status), "?", np.where(status == 0, "+", ""))
            return [left + right for left, right in zip(format_real(columns[:, 0]), suffix)]
        if kind == "left":
            status = columns[:, 1]
            suffix = np.where(np.isnan(status), "?", np.where(status == 0, "-", ""))
            return [left + right for left, right in zip(format_real(columns[:, 0]), suffix)]
        if kind == "counting":
            status = columns[:, 2]
            suffix = np.where(np.isnan(status), "?", np.where(status == 0, "+", ""))
            start = format_real(columns[:, 0])
            stop = format_real(columns[:, 1])
            return [f"({a},{b}{c}]" for a, b, c in zip(start, stop, suffix)]
        if kind == "interval":
            status = columns[:, 2]
            marks = np.array(["+", "", "-", "]"])
            time1 = format_real(columns[:, 0])
            time2 = format_real(columns[:, 1])
            labels = []
            for i, code in enumerate(status):
                if math.isnan(code):
                    labels.append("NA")
                elif int(code) == 3:
                    labels.append("[" + time1[i] + ", " + time2[i] + "]")
                else:
                    labels.append(time1[i] + marks[int(code)])
            return labels
        if kind in ("mright", "mcounting"):
            status = columns[:, 1] if kind == "mright" else columns[:, 2]
            if self.clabel is None:
                end = ["+"] + [":" + state for state in self.states]
            else:
                end = [":" + label for label in [self.clabel, *self.states]]
            if kind == "mright":
                times = format_real(columns[:, 0])
                labels = []
                for time, code in zip(times, status):
                    if math.isnan(code):
                        labels.append(time + "?")
                    else:
                        labels.append(time + end[int(code)])
                return labels
            start = format_real(columns[:, 0])
            stop = format_real(columns[:, 1])
            labels = []
            for a, b, code in zip(start, stop, status):
                mark = "?" if math.isnan(code) else end[int(code)]
                labels.append(f"({a},{b}{mark}]")
            return labels
        raise ValueError(f"unknown Surv type {kind}")

    def matrix(self):
        return np.array(self.columns, copy=True)

    def is_na(self):
        return np.any(np.isnan(self.columns), axis=1)


def Surv(time, time2=None, event=None, type=("right", "left", "interval", "counting", "interval2"), origin=0):
    """Build a survival response. A missing second argument is the status."""
    if time is None:
        raise ValueError("Must have a time argument")
    time = _as_float(time)
    if time is None or not np.issubdtype(np.asarray(time).dtype, np.number):
        raise ValueError("Time variable is not numeric")
    nn = time.size
    present_time2 = time2 is not None
    present_event = event is not None
    ng = 1 + int(present_time2) + int(present_event)
    supplied = type
    if not (isinstance(type, (list, tuple)) and list(type)[:5] == ["right", "left", "interval", "counting", "interval2"] and len(list(type)) == 5):
        if type == "mstate":
            warnings.warn("type= 'mstate' is deprecated, use a factor variable as status", stacklevel=2)
            mtype = "mstate"
        else:
            mtype = _match_type(type)
    else:
        mtype = "right"
    default_type = isinstance(supplied, (list, tuple))
    if default_type or mtype == "mstate":
        if ng in (1, 2):
            chosen = "right"
        elif ng == 3:
            chosen = "counting"
        else:
            raise ValueError("No time variable!")
    else:
        chosen = mtype
        if ng != 3 and chosen in ("interval", "counting"):
            raise ValueError("Wrong number of args for this type of survival data")
        if ng != 2 and chosen in ("right", "left", "interval2"):
            raise ValueError("Wrong number of args for this type of survival data")
    states = None
    clabel = None
    if ng == 1:
        columns = np.column_stack([time - origin, np.ones(nn)])
        chosen = "right"
    elif chosen in ("right", "left"):
        if not present_event:
            event = time2
            time2 = None
        event_values = event
        if _is_factor(event_values) or mtype == "mstate":
            levels = sorted(set(event_values))
            status = np.array([levels.index(item) for item in event_values], dtype=float)
            chosen = "mright"
            states = levels[1:]
            clabel = levels[0]
            if any(state is None or state == "" for state in states):
                raise ValueError("each state must have a non-blank name")
        else:
            event_array = _as_float(event_values)
            if event_array.size != nn:
                raise ValueError("Time and status are different lengths")
            observed = event_array[np.isfinite(event_array)]
            if observed.size and np.max(observed) == 2:
                status = event_array - 1
            else:
                status = event_array.copy()
            temp = (status == 0) | (status == 1)
            status = np.where(temp, status, np.nan)
            if observed.size and not np.all(temp[np.isfinite(event_array)]):
                warnings.warn("Invalid status value, converted to NA", stacklevel=2)
        columns = np.column_stack([time - origin, status])
    elif chosen == "counting":
        stop = _as_float(time2)
        event_array = event
        if stop.size != nn:
            raise ValueError("Start and stop are different lengths")
        if _is_factor(event_array) or mtype == "mstate":
            levels = sorted(set(event_array))
            status = np.array([levels.index(item) for item in event_array], dtype=float)
            chosen = "mcounting"
            states = levels[1:]
            clabel = levels[0]
        else:
            event_array = _as_float(event)
            if event_array.size != nn:
                raise ValueError("Start and event are different lengths")
            observed = event_array[np.isfinite(event_array)]
            if observed.size and np.max(observed) == 2:
                status = event_array - 1
            else:
                status = np.array(event_array, copy=True)
            temp = (status == 0) | (status == 1)
            status = np.where(temp, status, np.nan)
            if observed.size and not np.all(temp[np.isfinite(event_array)]):
                warnings.warn("Invalid status value, converted to NA", stacklevel=2)
        bad = time >= stop
        if np.any(bad & np.isfinite(time) & np.isfinite(stop)):
            time = np.array(time, copy=True)
            time[bad] = np.nan
            warnings.warn("Stop time must be > start time, NA created", stacklevel=2)
        columns = np.column_stack([time - origin, stop - origin, status])
    else:
        if chosen == "interval2":
            time2_array = _as_float(time2)
            if time2_array.size != nn:
                raise ValueError("time and time2 are different lengths")
            backwards = np.isfinite(time) & np.isfinite(time2_array) & (time > time2_array)
            time = np.where(np.isfinite(time), time, np.nan)
            time2_array = np.where(np.isfinite(time2_array), time2_array, np.nan)
            unknown = np.isnan(time) & np.isnan(time2_array)
            status = np.where(
                np.isnan(time),
                2,
                np.where(np.isnan(time2_array), 0, np.where(time == time2_array, 1, 3)),
            ).astype(float)
            time = np.where(status != 2, time, time2_array)
            if np.any(backwards):
                warnings.warn("Invalid interval: start > stop, NA created", stacklevel=2)
                status = np.array(status, copy=True)
                status[backwards] = np.nan
            if np.any(unknown):
                status = np.array(status, copy=True)
                status[unknown] = np.nan
            chosen = "interval"
            time2_out = np.where((~np.isnan(status)) & (status == 3), time2_array - origin, 1.0)
        else:
            event_array = _as_float(event)
            if event_array.size != nn:
                raise ValueError("Time and status are different lengths")
            temp = (event_array == 0) | (event_array == 1) | (event_array == 2) | (event_array == 3)
            status = np.where(temp, event_array, np.nan)
            if not np.all(temp[np.isfinite(event_array)]):
                warnings.warn("Status must be 0, 1, 2 or 3; converted to NA", stacklevel=2)
            if np.any(event_array == 3):
                time2_array = _as_float(time2)
                if time2_array.size != nn:
                    raise ValueError("time and time2 are different lengths")
                bad = (status == 3) & (time > time2_array)
                if np.any(bad & np.isfinite(time) & np.isfinite(time2_array)):
                    status = np.array(status, copy=True)
                    status[bad] = np.nan
                    warnings.warn("Invalid interval: start > stop, NA created", stacklevel=2)
                time2_out = np.where((~np.isnan(status)) & (status == 3), time2_array - origin, 1.0)
            else:
                time2_out = np.ones(nn)
        columns = np.column_stack([time - origin, time2_out, status])
    return SurvObject(columns, chosen, states, clabel)


def is_Surv(x):
    """True when x is a Surv response."""
    return isinstance(x, SurvObject)


def format_Surv(x):
    """Character labels of a Surv response, padded to a common width."""
    labels = x.character()
    width = max((len(item) for item in labels), default=0)
    return [item.ljust(width) for item in labels]


def is_na_Surv(x):
    """True for a row with any missing time or status."""
    return x.is_na()


def _find_interval(values, cuts):
    """R findInterval. 0 when x is below the first cut."""
    index = np.searchsorted(cuts, values, side="right") - 1
    index = index.astype(int)
    index[np.isnan(values)] = -1
    return index


def aeqSurv(x, tolerance=None):
    """Collapse times that all.equal would treat as tied."""
    if tolerance is None:
        tolerance = math.sqrt(2.220446049250313e-16)
    else:
        tolerance = float(tolerance)
        if not math.isfinite(tolerance):
            raise ValueError("invalid value for tolerance")
        if tolerance <= 0:
            return x
    if not isinstance(x, SurvObject):
        raise ValueError("argument is not a Surv object")
    times = x.columns[:, :-1].reshape(-1)
    finite = times[np.isfinite(times)]
    y = np.unique(finite)
    if y.size < 2:
        return x
    dy = np.diff(y)
    scale = np.mean(np.abs(y))
    tied = (dy <= tolerance) | ((dy / scale) <= tolerance)
    if not np.any(tied):
        return x
    keep = np.concatenate([[True], ~tied])
    cuts = y[keep]
    if x.columns.shape[1] == 2:
        z = _find_interval(x.columns[:, 0], cuts)
        mapped = np.where(z >= 0, cuts[np.clip(z, 0, cuts.size - 1)], np.nan)
        mapped[z < 0] = np.nan
        columns = np.column_stack([mapped, x.columns[:, 1]])
    else:
        z = np.column_stack([
            _find_interval(x.columns[:, 0], cuts),
            _find_interval(x.columns[:, 1], cuts),
        ])
        zeros = np.where(z[:, 0] == z[:, 1])[0]
        if zeros.size and np.any(x.columns[zeros, 0] != x.columns[zeros, 1]):
            raise ValueError("aeqSurv exception, an interval has effective length 0")
        mapped = np.where(z >= 0, cuts[np.clip(z, 0, cuts.size - 1)], np.nan)
        columns = np.column_stack([mapped, x.columns[:, 2]])
    return SurvObject(columns, x.type, x.states, x.clabel)
