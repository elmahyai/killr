"""Apply a function over slide and hop windows."""

from __future__ import annotations

import math

import numpy as np

from slider.errors import SliderError
from slider.index import complete_ranges, plan_from_before, plan_from_bounds
from slider.windows import iter_opts, slice_at, windows


def as_vector(x) -> list:
    if isinstance(x, np.ndarray):
        if x.ndim != 1:
            raise SliderError("`x` must be a vector.")
        return [_plain(value) for value in x.tolist()]
    if isinstance(x, (str, bytes)):
        raise SliderError("`x` must be a vector.")
    if isinstance(x, (list, tuple)):
        return [_plain(value) for value in x]
    if x is None or isinstance(x, (bool, int, float)):
        return [_plain(x)]
    raise SliderError("`x` must be a vector.")


def _plain(value):
    if isinstance(value, np.generic):
        value = value.item()
    return value


def _callable(fn):
    if not callable(fn):
        raise SliderError("`.f` must be a function.")
    return fn


def _size(value) -> int:
    if value is None or isinstance(value, (bool, int, float, str)):
        return 1
    if isinstance(value, np.ndarray):
        return int(value.size)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _scalar(value, kind: str | None):
    if kind is None:
        return value
    if _size(value) != 1:
        return value
    if isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]
    if isinstance(value, np.ndarray) and value.size == 1:
        value = value.item()
    if kind == "list":
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None if kind in ("int", "lgl", "chr") else math.nan
    if kind == "dbl":
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        raise SliderError("The result of `.f` must be a number.")
    if kind == "int":
        if isinstance(value, bool):
            raise SliderError("The result of `.f` must be an integer.")
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        raise SliderError("The result of `.f` must be an integer.")
    if kind == "lgl":
        if isinstance(value, bool):
            return value
        if value in (0, 1):
            return bool(value)
        raise SliderError("The result of `.f` must be logical.")
    if kind == "chr":
        if isinstance(value, str):
            return value
        raise SliderError("The result of `.f` must be a string.")
    return value


def _blank(kind: str | None):
    if kind in (None, "list"):
        return None
    if kind == "dbl":
        return math.nan
    return None


def _simplify(values: list, ptype: str | None):
    if ptype == "dbl":
        return [_scalar(value, "dbl") for value in values]
    if ptype == "int":
        return [_scalar(value, "int") for value in values]
    if ptype == "lgl":
        return [_scalar(value, "lgl") for value in values]
    if ptype == "chr":
        return [_scalar(value, "chr") for value in values]
    if ptype == "list":
        return values
    # slide_vec: one common atomic type, with missing positions as NA.
    kinds = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        if isinstance(value, bool):
            kinds.append("lgl")
        elif isinstance(value, int):
            kinds.append("int")
        elif isinstance(value, float):
            kinds.append("dbl")
        elif isinstance(value, str):
            kinds.append("chr")
        else:
            return values
    if not kinds:
        return [None] * len(values)
    if "chr" in kinds:
        kind = "chr"
    elif "dbl" in kinds:
        kind = "dbl"
    elif "int" in kinds and "lgl" not in kinds:
        kind = "int"
    elif "lgl" in kinds and "int" not in kinds:
        kind = "lgl"
    else:
        kind = "dbl"
    return [_scalar(None if value is None else value, kind) for value in values]


def _check_size(value, index: int, atomic: bool) -> None:
    if atomic and _size(value) != 1:
        raise SliderError(
            f"In index: {index}. The result of `.f` must have size 1, not {_size(value)}."
        )


def recycle(vectors: list[list]) -> list[list]:
    if not vectors:
        return []
    lengths = [len(vector) for vector in vectors]
    size = max(lengths)
    out = []
    for vector, length in zip(vectors, lengths):
        if length == size:
            out.append(vector)
        elif length == 1:
            out.append(vector * size)
        elif length == 0 and size == 0:
            out.append([])
        else:
            raise SliderError(f"Can't recycle a vector of size {length} to size {size}.")
    return out


def _prepare(groups: list, fn, args):
    fn = _callable(fn)
    vectors = recycle([as_vector(group) for group in groups])
    return fn, vectors, args


def slide_apply(groups: list, fn, args, before, after, step, complete, *, kind: str | None, atomic: bool, simplify: bool):
    fn, vectors, args = _prepare(groups, fn, args)
    if not vectors:
        return []
    size = len(vectors[0])
    opts = iter_opts(before, after, step, complete, size, dot=True)
    out = [_blank(kind if not simplify else None) for _ in range(size)]
    for index, start, stop in windows(opts):
        slices = [slice_at(vector, start, stop) for vector in vectors]
        value = fn(*slices, *args)
        _check_size(value, index + 1, atomic)
        out[index] = value if kind == "list" else value
    if kind == "list":
        return out
    if simplify:
        return _simplify(out, None)
    return [_scalar(value, kind) if value is not _blank(kind) or kind == "dbl" else value for value in out]


def _placed(out, kind, value, atomic, index):
    _check_size(value, index + 1, atomic)
    out[index] = value


def hop_apply(groups: list, starts, stops, fn, args, *, kind: str | None, atomic: bool, simplify: bool):
    fn, vectors, args = _prepare(groups, fn, args)
    starts = [_int_position(value, ".starts") for value in as_vector(starts)]
    stops = [_int_position(value, ".stops") for value in as_vector(stops)]
    if len(starts) == 1 and len(stops) != 1:
        starts = starts * len(stops)
    elif len(stops) == 1 and len(starts) != 1:
        stops = stops * len(starts)
    elif len(starts) != len(stops):
        raise SliderError(
            f"`.starts` ({len(starts)}) and `.stops` ({len(stops)}) must have the same size."
        )
    locations = [i + 1 for i, (start, stop) in enumerate(zip(starts, stops)) if start > stop]
    if locations:
        shown = ", ".join(str(item) for item in locations)
        raise SliderError(
            f"In locations: {shown}. In the ranges generated by `.starts` and `.stops`: "
            "The start of the range can't be after the end of the range."
        )
    size = len(starts)
    x_size = len(vectors[0]) if vectors else 0
    out = [_blank(kind if not simplify else None) for _ in range(size)]
    for index, (start, stop) in enumerate(zip(starts, stops)):
        window_start = max(start - 1, 0)
        window_stop = min(stop - 1, x_size - 1)
        if window_stop < window_start:
            bounds = (None, None)
        else:
            bounds = (window_start, window_stop)
        slices = [slice_at(vector, bounds[0], bounds[1]) for vector in vectors]
        value = fn(*slices, *args)
        _check_size(value, index + 1, atomic)
        out[index] = value
    if kind == "list":
        return out
    if simplify:
        return _simplify(out, None)
    return [_scalar(value, kind) for value in out]


def _int_position(value, label: str) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise SliderError(f"`{label}` can't be missing.")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SliderError(f"`{label}` must be an integer.")
    if isinstance(value, float) and not value.is_integer():
        raise SliderError(f"`{label}` must be an integer.")
    return int(value)


def slide_index_apply(groups, index, fn, args, before, after, complete, *, kind, atomic, simplify):
    fn, vectors, args = _prepare(groups, fn, args)
    index = as_vector(index)
    if vectors and len(index) != len(vectors[0]):
        raise SliderError(
            f"`.i` must have size {len(vectors[0])}, not {len(index)}."
        )
    plan = plan_from_before(index, before, after, complete)
    out = [_blank(kind if not simplify else None) for _ in range(len(index))]
    for pos, start, stop in complete_ranges(plan):
        slices = [slice_at(vector, start, stop) for vector in vectors]
        value = fn(*slices, *args)
        _check_size(value, pos + 1, atomic)
        element = plan.peer_starts[pos]
        for _ in range(plan.times[pos]):
            out[element] = value
            element += 1
    if kind == "list":
        return out
    if simplify:
        return _simplify(out, None)
    return [_scalar(value, kind) for value in out]


def hop_index_apply(groups, index, starts, stops, fn, args, *, kind, atomic, simplify):
    fn, vectors, args = _prepare(groups, fn, args)
    index = as_vector(index)
    if vectors and len(index) != len(vectors[0]):
        raise SliderError(
            f"`.i` must have size {len(vectors[0])}, not {len(index)}."
        )
    plan = plan_from_bounds(index, as_vector(starts), as_vector(stops))
    out = [_blank(kind if not simplify else None) for _ in range(len(plan.starts))]
    for pos, start, stop in plan.ranges():
        slices = [slice_at(vector, start, stop) for vector in vectors]
        value = fn(*slices, *args)
        _check_size(value, pos + 1, atomic)
        out[pos] = value
    if kind == "list":
        return out
    if simplify:
        return _simplify(out, None)
    return [_scalar(value, kind) for value in out]
