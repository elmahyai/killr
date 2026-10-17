"""The Surv2 timeline response, from survival::Surv2."""

import math
import warnings

import numpy as np

from survival.formatreal import format_real


class FactorEvent:
    """Factor-style event codes with explicit level order (first level is censor)."""

    def __init__(self, values, levels):
        self.values = list(values)
        self.levels = list(levels)

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)


class Surv2Object:
    """Timeline survival response with time and status columns."""

    def __init__(
        self,
        columns,
        *,
        states=None,
        clabel=None,
        input_attributes=None,
        repeated=False,
        colnames=("time", "status"),
    ):
        self.columns = np.array(columns, dtype=float, copy=True)
        if self.columns.ndim == 1:
            self.columns = self.columns.reshape(-1, 1)
        self.states = None if states is None else list(states)
        self.clabel = clabel
        self.input_attributes = input_attributes
        self.repeated = repeated
        self.colnames = list(colnames)

    def __len__(self):
        return int(self.columns.shape[0])

    def __repr__(self):
        return " ".join(self.character())

    def matrix(self):
        out = np.array(self.columns, copy=True)
        return out

    def character(self):
        times = format_real(self.columns[:, 0])
        status = self.columns[:, 1]
        if self.states is None:
            suffix = np.where(np.isnan(status), "?", np.where(status == 0, "+", ""))
            return [left + right for left, right in zip(times, suffix)]
        if self.clabel is None:
            end = ["+"] + [":" + state for state in self.states]
        else:
            end = [":" + label for label in [self.clabel, *self.states]]
        labels = []
        for time, code in zip(times, status):
            if math.isnan(code):
                labels.append(time + "?")
            else:
                labels.append(time + end[int(code)])
        return labels

    def is_na(self):
        return np.any(np.isnan(self.columns), axis=1)


def _as_float(values):
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        array = array.reshape(1)
    return array.reshape(-1)


def _is_factor_event(event):
    return isinstance(event, FactorEvent) or (
        hasattr(event, "levels") and not isinstance(event, (str, bytes))
    )


def _factor_values(event):
    if isinstance(event, FactorEvent):
        return event.values, event.levels
    return list(event), list(event.levels)


def _all_logical_or_na(event):
    for value in event:
        if value is None:
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        if not isinstance(value, (bool, np.bool_)):
            return False
    return True


def _validate_repeated(repeated):
    if isinstance(repeated, str):
        if repeated == "first":
            return repeated
        raise ValueError("invalid value for repeated option")
    if isinstance(repeated, (bool, np.bool_)):
        return bool(repeated)
    raise ValueError("invalid value for repeated option")


def Surv2(time, event, repeated=False):
    """Build a timeline-style survival response from time and event."""
    if time is None:
        raise ValueError("must have a time argument")
    if hasattr(time, "total_seconds"):
        time = [item.total_seconds() for item in np.atleast_1d(time)]
    time = _as_float(time)
    if not np.issubdtype(time.dtype, np.number):
        raise ValueError("Time variable is not numeric")
    nn = time.size
    repeated = _validate_repeated(repeated)

    if event is None:
        raise ValueError("must have an event argument")

    input_attributes = {}
    time_attrs = getattr(time, "attrs", None) or getattr(time, "attributes", None)
    if time_attrs:
        input_attributes["time"] = dict(time_attrs)
    event_attrs = getattr(event, "attrs", None) or getattr(event, "attributes", None)
    if event_attrs:
        input_attributes["event"] = dict(event_attrs)

    states = None
    clabel = None

    if _is_factor_event(event):
        values, levels = _factor_values(event)
        if len(values) != nn:
            raise ValueError("Time and event are different lengths")
        states = levels[1:]
        clabel = levels[0]
        if any(state is None or state == "" for state in states):
            raise ValueError("each state must have a non-blank name")
        index = {level: code for code, level in enumerate(levels, start=1)}
        status = np.array(
            [float(index[value]) - 1.0 if value in index else math.nan for value in values],
            dtype=float,
        )
    else:
        if isinstance(event, np.ndarray):
            event_seq = event.tolist()
        elif isinstance(event, (list, tuple)):
            event_seq = list(event)
        else:
            try:
                event_seq = list(event)
            except TypeError:
                event_seq = [event]

        if _all_logical_or_na(event_seq):
            if len(event_seq) != nn:
                raise ValueError("Time and event are different lengths")
            status = np.array(
                [
                    math.nan
                    if item is None or (isinstance(item, float) and math.isnan(item))
                    else float(int(bool(item)))
                    for item in event_seq
                ],
                dtype=float,
            )
        else:
            event_array = _as_float(event)
            if event_array.size != nn:
                raise ValueError("Time and event are different lengths")
            observed = event_array[np.isfinite(event_array)]
            status = np.array(event_array, copy=True, dtype=float)
            if observed.size and np.max(observed) == 2:
                status = status - 1.0
            valid = (status == 0) | (status == 1)
            if observed.size and not np.all(valid[np.isfinite(event_array)]):
                warnings.warn("Invalid status value, converted to NA", stacklevel=2)
            status = np.where(valid, status, np.nan)

    columns = np.column_stack([time, status])
    if not input_attributes:
        input_attributes = None

    return Surv2Object(
        columns,
        states=states,
        clabel=clabel,
        input_attributes=input_attributes,
        repeated=repeated,
    )
