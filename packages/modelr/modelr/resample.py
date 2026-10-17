"""Resamples, bootstrap replicates, partitions, permutations, and cross-validation.

Draws use the same Mersenne Twister as the boot translation, so set.seed
in R and boot.rng.set_seed here produce the same indexes.
"""

from __future__ import annotations

import sys
from pathlib import Path

from modelr.frame import Frame, as_frame


def _rng():
    try:
        from boot import rng as module
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot import rng as module
    return module


def _sample_int(n, size=None, replace=False):
    return _rng().sample_int(n, size, replace)


def _one_number(value, message):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    if isinstance(value, float) and value != value:
        raise ValueError(message)


def _int_vector(idx):
    if isinstance(idx, (str, bytes, int, float, bool)):
        return None
    try:
        values = list(idx)
    except TypeError:
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        return None
    return values


def _id_labels(n):
    width = len(str(int(n)))
    return [f"{i:0{width}d}" for i in range(1, int(n) + 1)]


def _big_mark(value):
    text = str(int(value))
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    groups = []
    while text:
        groups.append(text[-3:])
        text = text[:-3]
    return sign + ",".join(reversed(groups))


def _preview(idx):
    shown = list(idx[:10])
    text = ", ".join(str(value) for value in shown)
    if len(idx) > 10:
        text += ", ..."
    return text


class Resample:
    def __init__(self, data, idx):
        self.data = data
        self.idx = list(idx)

    def as_frame(self):
        return self.data.subset(self.idx)

    @property
    def nrow(self):
        return len(self.idx)

    @property
    def ncol(self):
        return self.data.ncol

    def obj_sum(self):
        return f"resample [{_big_mark(self.nrow)} x {_big_mark(self.ncol)}]"

    def __str__(self):
        return f"<{self.obj_sum()}> {_preview(self.idx)}"

    def __repr__(self):
        return str(self)


class Permutation:
    def __init__(self, data, columns, idx):
        self.data = data
        self.columns = list(columns)
        self.idx = list(idx)

    def as_frame(self):
        out = self.data.copy()
        positions = [i - 1 for i in self.idx]
        for name in self.columns:
            values = out.columns[name]
            if hasattr(values, "take"):
                out.columns[name] = values.take(positions)
            else:
                out.columns[name] = [values[i] for i in positions]
        return out

    @property
    def nrow(self):
        return len(self.idx)

    @property
    def ncol(self):
        return self.data.ncol

    def obj_sum(self):
        names = ", ".join(self.columns)
        return f"permutation ({names}) [{_big_mark(self.nrow)} x {_big_mark(self.ncol)}]"

    def __str__(self):
        return f"<{self.obj_sum()}> {_preview(self.idx)}"

    def __repr__(self):
        return str(self)


def resample(data, idx):
    if not isinstance(data, Frame):
        raise ValueError("`data` must be a data frame.")
    values = _int_vector(idx)
    if values is None:
        raise ValueError("`idx` must be an integer vector.")
    return Resample(data, values)


def resample_bootstrap(data):
    frame = as_frame(data)
    n = frame.nrow
    return resample(frame, _sample_int(n, n, replace=True))


def bootstrap(data, n, id=".id"):
    frame = as_frame(data)
    count = int(n)
    straps = [resample_bootstrap(frame) for _ in range(count)]
    return Frame({"strap": straps, id: _id_labels(count)})


def _find_interval(x, breaks):
    """findInterval with the rightmost break closed."""
    if x < breaks[0]:
        return 0
    if x == breaks[-1]:
        return len(breaks) - 1
    if x > breaks[-1]:
        return len(breaks)
    index = 0
    for position, edge in enumerate(breaks):
        if edge <= x:
            index = position + 1
        else:
            break
    return index


def resample_partition(data, p):
    if not isinstance(p, dict) or len(p) < 2:
        raise ValueError("`p` must be a named numeric vector with at least two values.")
    names = list(p)
    values = []
    for name in names:
        value = p[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("`p` must be a named numeric vector with at least two values.")
        if name is None or name == "":
            raise ValueError("`p` must be a named numeric vector with at least two values.")
        values.append(float(value))
    total = sum(values)
    if abs(total - 1) > 1e-6:
        print("Rescaling `p` to sum to 1.", file=sys.stderr)
    values = [value / total for value in values]
    frame = as_frame(data)
    n = frame.nrow
    breaks = [0.0]
    running = 0.0
    for value in values:
        running += value
        breaks.append(running)
    labels = [_find_interval(i / n, breaks) for i in range(1, n + 1)]
    order = _sample_int(n, n, replace=False)
    permuted = [labels[i - 1] for i in order]
    buckets = {label: [] for label in range(1, len(values) + 1)}
    for row, label in zip(range(1, n + 1), permuted):
        buckets[label].append(row)
    return {name: resample(frame, buckets[label]) for label, name in enumerate(names, start=1)}


def resample_permutation(data, columns, idx=None):
    if idx is None:
        if isinstance(data, Frame):
            idx = _sample_int(data.nrow, data.nrow, replace=False)
        else:
            idx = _sample_int(0)
    if not isinstance(data, Frame):
        raise ValueError("`data` must be a data frame.")
    if (
        isinstance(columns, (str, bytes))
        or not isinstance(columns, (list, tuple))
        or not all(isinstance(name, str) and name in data.names() for name in columns)
    ):
        raise ValueError("`columns` must be a vector of column names in `data`")
    values = _int_vector(idx)
    if values is None or len(values) != data.nrow:
        raise ValueError(
            "`idx` must be an integer vector with the same length as there are rows in `data`"
        )
    return Permutation(data, columns, values)


def permute_(data, n, columns, id=".id"):
    frame = as_frame(data)
    count = int(n)
    perms = [resample_permutation(frame, list(columns)) for _ in range(count)]
    return Frame({"perm": perms, id: _id_labels(count)})


def permute(data, n, *columns, id=".id"):
    frame = as_frame(data)
    names = _select_columns(frame.names(), columns)
    return permute_(frame, n, names, id=id)


def _select_columns(available, columns):
    if len(columns) == 1 and isinstance(columns[0], (list, tuple)):
        columns = tuple(columns[0])
    chosen = []
    for column in columns:
        if isinstance(column, str) and ":" in column and column not in available:
            start, end = column.split(":", 1)
            if start not in available or end not in available:
                raise ValueError("`columns` must be a vector of column names in `data`")
            i = available.index(start)
            j = available.index(end)
            step = 1 if i <= j else -1
            chosen.extend(available[i : j + step : step])
            continue
        if not isinstance(column, str) or column not in available:
            raise ValueError("`columns` must be a vector of column names in `data`")
        chosen.append(column)
    return chosen


def _folds(n, k):
    labels = [(i % k) + 1 for i in range(n)]
    order = _sample_int(n, n, replace=False)
    return [labels[i - 1] for i in order]


def crossv_kfold(data, k=5, id=".id"):
    _one_number(k, "`k` must be a single integer.")
    frame = as_frame(data)
    n = frame.nrow
    folds = int(k)
    assigned = _folds(n, folds)
    groups = {label: [] for label in range(1, folds + 1)}
    for row, label in zip(range(1, n + 1), assigned):
        groups[label].append(row)
    every = list(range(1, n + 1))
    trains = []
    tests = []
    for label in range(1, folds + 1):
        test = groups[label]
        held = set(test)
        trains.append(resample(frame, [row for row in every if row not in held]))
        tests.append(resample(frame, test))
    return Frame({"train": trains, "test": tests, id: _id_labels(folds)})


def crossv_loo(data, id=".id"):
    frame = as_frame(data)
    n = frame.nrow
    every = list(range(1, n + 1))
    trains = []
    tests = []
    for row in every:
        trains.append(resample(frame, [other for other in every if other != row]))
        tests.append(resample(frame, [row]))
    return Frame({"train": trains, "test": tests, id: every})


def crossv_mc(data, n, test=0.2, id=".id"):
    _one_number(n, "`n` must be a single integer.")
    _one_number(test, "`test` must be a value between 0 and 1.")
    if test <= 0 or test >= 1:
        raise ValueError("`test` must be a value between 0 and 1.")
    frame = as_frame(data)
    count = int(n)
    share = {"train": 1 - test, "test": test}
    runs = [resample_partition(frame, share) for _ in range(count)]
    return Frame(
        {
            "train": [run["train"] for run in runs],
            "test": [run["test"] for run in runs],
            id: _id_labels(count),
        }
    )
