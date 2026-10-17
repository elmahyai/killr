"""iter, nextElem, and icount from iterators 1.0.14.

``iter`` dispatches the way ``UseMethod`` does. A matrix is a two-dimensional
NumPy array, filled and read down columns. A data frame is a ``DataFrame``.
A list or tuple is an atomic vector when its elements are values, and a
function becomes a ``funiter``. ``icount`` returns an ``abstractiter``.
``nextElem`` stops with ``IteratorError('StopIteration')``.
"""

from __future__ import annotations

import inspect
import math
import warnings

import numpy as np


_MISSING = object()
_BY_MATRIX = ("column", "cell", "row")
_BY_FRAME = ("column", "row")
_ALWAYS = object()


class IteratorError(Exception):
    """An R ``stop`` from this package, including ``StopIteration``."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class State:
    def __init__(self, i=0, obj=None, fun=None):
        self.i = i
        self.obj = obj
        self.fun = fun


class Iter:
    """An iterator list. ``classes`` is the S3 class vector, first match wins."""

    def __init__(self, classes, **fields):
        self.classes = list(classes)
        for key, value in fields.items():
            setattr(self, key, value)

    def __repr__(self):
        return "Iter(" + ", ".join(self.classes) + ")"


class DataFrame:
    """A data frame: named columns of equal length, row names ``1`` onward.

    A length-1 column is repeated to the longest column, as ``data.frame`` does.
    """

    def __init__(self, columns, row_names=None):
        if not isinstance(columns, dict) or not columns:
            raise IteratorError("arguments imply differing number of rows: 0")
        self.names = [str(name) for name in columns]
        stored = {name: _as_column(columns[name]) for name in columns}
        width = max(len(values) for values in stored.values())
        for name, values in stored.items():
            if len(values) == width:
                continue
            if len(values) == 1:
                stored[name] = values * width
                continue
            if width % len(values) == 0:
                stored[name] = values * (width // len(values))
                continue
            raise IteratorError(
                "arguments imply differing number of rows: "
                + ", ".join(str(len(item)) for item in stored.values())
            )
        self.columns = {str(name): values for name, values in stored.items()}
        self.nrow = width
        if row_names is None:
            self.row_names = [str(index) for index in range(1, width + 1)]
        else:
            self.row_names = [str(name) for name in row_names]

    def __len__(self):
        return len(self.names)


def _as_column(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, bool):
        return [value]
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, np.ndarray):
        return [_scalar(item) for item in np.ravel(value, order="F")]
    if isinstance(value, (list, tuple)):
        return list(value)
    raise IteratorError("unsupported column type")


def _scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    return value


def _always_true(*_args):
    return True


def _resolve_check(check):
    if check is None or check is _ALWAYS:
        return _always_true
    return check


def match_arg(arg, choices):
    """``match.arg``: NULL or an exact copy of ``choices`` is the first choice.

    A unique prefix is kept. Anything else is the ``should be one of`` error,
    and the choices are wrapped in the quotes ``dQuote`` uses.
    """
    choices = tuple(choices)
    if arg is None:
        return choices[0]
    if isinstance(arg, (list, tuple)):
        if list(arg) == list(choices):
            return choices[0]
        raise IteratorError("'arg' must be of length 1")
    if not isinstance(arg, str):
        raise IteratorError("'arg' must be NULL or a character vector")
    exact = [choice for choice in choices if choice == arg]
    if len(exact) == 1:
        return exact[0]
    partial = [choice for choice in choices if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices if choice)
    raise IteratorError(f"'arg' should be one of {quoted}")


def _bind(names, defaults, args, kwargs):
    bound = dict(defaults)
    seen = set()
    for name, value in zip(names, args):
        bound[name] = value
        seen.add(name)
    for key, value in kwargs.items():
        if key not in defaults:
            continue
        if key in seen:
            raise IteratorError(
                f'formal argument "{key}" matched by multiple actual arguments'
            )
        bound[key] = value
    return bound


def _kind(obj):
    if isinstance(obj, Iter):
        for name in obj.classes:
            if name == "matrix":
                return "matrix"
            if name == "data.frame":
                return "data.frame"
            if name == "function":
                return "function"
            if name == "iter":
                return "iter"
        return "default"
    if isinstance(obj, DataFrame):
        return "data.frame"
    if isinstance(obj, np.ndarray) and obj.ndim == 2:
        return "matrix"
    if callable(obj):
        return "function"
    return "default"


def _has_formals(fun):
    try:
        signature = inspect.signature(fun)
    except (TypeError, ValueError):
        return False
    return len(signature.parameters) > 0


def _colon(start, end):
    """R ``start:end``. The step is 1 or -1, and the length is ``floor`` of the span."""
    start = float(start)
    end = float(end)
    if start <= end:
        count = int(math.floor(end - start)) + 1
        values = [start + offset for offset in range(count)]
    else:
        count = int(math.floor(start - end)) + 1
        values = [start - offset for offset in range(count)]
    return [int(value) if float(value).is_integer() else value for value in values]


def _greater_than_one(chunksize):
    if isinstance(chunksize, bool) or not isinstance(chunksize, (int, float, np.integer, np.floating)):
        raise IteratorError("comparison of these types is not implemented")
    number = float(chunksize)
    if math.isnan(number):
        raise IteratorError("missing value where TRUE/FALSE needed")
    return number > 1


def _flag(value):
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise IteratorError("the condition has length > 1")
        value = value.item()
    elif isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise IteratorError("the condition has length > 1")
        value = value[0]
    if isinstance(value, np.generic):
        value = value.item()
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise IteratorError("missing value where TRUE/FALSE needed")
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float)):
        return value != 0
    raise IteratorError("argument is not interpretable as logical")


def _message_of(exc):
    if type(exc) is StopIteration:
        text = exc.args[0] if exc.args else ""
        return "StopIteration" if text in ("", "StopIteration") else str(text)
    if isinstance(exc, IteratorError):
        return exc.message
    return str(exc)


def _recover(obj, exc, bounds, args_only=False):
    # ``any(nzchar(message))`` is false only when the message is empty.
    message = _message_of(exc)
    if message == "":
        raise IteratorError("Abort")
    if message in bounds:
        if obj.recycle and (obj.args if args_only else True):
            obj.state.i = 0
            return
        if obj.recycle and args_only and not obj.args:
            return
        raise IteratorError("StopIteration")
    raise IteratorError(message)


def _container_length(obj):
    if obj is None:
        return 0
    if isinstance(obj, (str, bytes)):
        return 1
    if isinstance(obj, dict):
        return len(obj)
    if isinstance(obj, np.ndarray):
        return int(obj.size)
    try:
        return len(obj)
    except TypeError:
        return 1


def _container_item(obj, index):
    if isinstance(obj, (str, bytes)):
        return obj
    if isinstance(obj, dict):
        return list(obj.values())[index - 1]
    if isinstance(obj, np.ndarray):
        flat = np.ravel(obj, order="F")
        return _scalar(flat[index - 1])
    return obj[index - 1]


def _get_container(obj, plus):
    index = obj.state.i + plus
    if index > obj.length:
        raise IteratorError("SubscriptOutOfBounds")
    return _container_item(obj.state.obj, index)


def _subset_2d(arr, positions, axis):
    slots = [position - 1 for position in positions]
    if axis == 1:
        return arr[:, slots].copy()
    return np.asarray(arr[slots, :]).reshape(len(slots), arr.shape[1]).copy()


def _get_matrix(obj, plus):
    index = obj.state.i + plus
    length = obj.length
    if index > length:
        raise IteratorError("SubscriptOutOfBounds")
    end = min(index + obj.chunksize - 1, length)
    if obj.by == "column":
        return _subset_2d(obj.state.obj, _colon(index, end), axis=1)
    if obj.by == "row":
        return _subset_2d(obj.state.obj, _colon(index, end), axis=0)
    row_count = obj.state.obj.shape[0]
    cursor = int(index) - 1
    return _scalar(obj.state.obj[cursor % row_count, cursor // row_count])


def _get_frame(obj, plus):
    index = obj.state.i + plus
    if index > obj.length:
        raise IteratorError("StopIteration")
    frame = obj.state.obj
    if obj.by == "column":
        name = frame.names[index - 1]
        return list(frame.columns[name])
    columns = {
        name: [frame.columns[name][index - 1]] for name in frame.names
    }
    return DataFrame(columns, row_names=[frame.row_names[index - 1]])


def _call_check(check, value):
    if not callable(check):
        raise IteratorError("attempt to apply non-function")
    return check(value)


def _next_container(obj):
    while True:
        try:
            if _flag(_call_check(obj.checkFunc, _get_container(obj, 1))):
                obj.state.i = obj.state.i + 1
                return _get_container(obj, 0)
            obj.state.i = obj.state.i + 1
        except Exception as exc:
            _recover(obj, exc, {"SubscriptOutOfBounds"})


def _next_matrix(obj):
    while True:
        try:
            if _flag(_call_check(obj.checkFunc, _get_matrix(obj, 1))):
                obj.state.i = obj.state.i + obj.chunksize
                return _get_matrix(obj, 1 - obj.chunksize)
            obj.state.i = obj.state.i + obj.chunksize
        except Exception as exc:
            _recover(
                obj,
                exc,
                {"SubscriptOutOfBounds", "attempt to select more than one element"},
            )


def _next_frame(obj):
    while True:
        try:
            if _flag(_call_check(obj.checkFunc, _get_frame(obj, 1))):
                obj.state.i = obj.state.i + 1
                return _get_frame(obj, 0)
            obj.state.i = obj.state.i + 1
        except Exception as exc:
            _recover(obj, exc, {"StopIteration"})


def _next_fun(obj):
    while True:
        try:
            if obj.args:
                value = obj.state.fun(obj.state.i + 1)
            else:
                value = obj.state.fun()
            if _flag(_call_check(obj.checkFunc, value)):
                if obj.args:
                    obj.state.i = obj.state.i + 1
                return value
            if obj.args:
                obj.state.i = obj.state.i + 1
        except Exception as exc:
            _recover(obj, exc, {"StopIteration"}, args_only=True)


def _next_abstract(obj):
    return obj.nextElem()


_NEXT = {
    "containeriter": _next_container,
    "matrixiter": _next_matrix,
    "dataframeiter": _next_frame,
    "funiter": _next_fun,
    "abstractiter": _next_abstract,
}


def nextElem(obj, *args, **kwargs):
    """Return the next value that ``checkFunc`` accepts.

    Extra arguments are ignored. The end of the iterator is
    ``IteratorError('StopIteration')``.
    """
    del args, kwargs
    if isinstance(obj, Iter):
        for name in obj.classes:
            method = _NEXT.get(name)
            if method is not None:
                return method(obj)
    raise IteratorError(
        "no applicable method for 'nextElem' applied to an object of class "
        + ", ".join(getattr(obj, "classes", ["NULL"]))
    )


def _iter_self(obj, *args, **kwargs):
    del args, kwargs
    return obj


def _iter_default(obj, *args, **kwargs):
    bound = _bind(
        ("checkFunc", "recycle"),
        {"checkFunc": _ALWAYS, "recycle": False},
        args,
        kwargs,
    )
    state = State(i=0, obj=obj)
    return Iter(
        ["containeriter", "iter"],
        state=state,
        length=_container_length(obj),
        checkFunc=_resolve_check(bound["checkFunc"]),
        recycle=bound["recycle"],
    )


def _iter_matrix(obj, *args, **kwargs):
    bound = _bind(
        ("by", "chunksize", "checkFunc", "recycle"),
        {
            "by": list(_BY_MATRIX),
            "chunksize": 1,
            "checkFunc": _ALWAYS,
            "recycle": False,
        },
        args,
        kwargs,
    )
    by = match_arg(bound["by"], _BY_MATRIX)
    chunksize = bound["chunksize"]
    if _greater_than_one(chunksize) and by == "cell":
        warnings.warn(
            "Chunksize greater than 1 not allowed when using by='cell'\n  Setting chunksize=1",
            UserWarning,
            stacklevel=3,
        )
        chunksize = 1
    if by == "column":
        length = int(obj.shape[1])
    elif by == "row":
        length = int(obj.shape[0])
    else:
        length = int(obj.shape[0] * obj.shape[1])
    return Iter(
        ["matrixiter", "iter"],
        state=State(i=0, obj=obj),
        by=by,
        length=length,
        checkFunc=_resolve_check(bound["checkFunc"]),
        recycle=bound["recycle"],
        chunksize=chunksize,
    )


def _iter_frame(obj, *args, **kwargs):
    bound = _bind(
        ("by", "checkFunc", "recycle"),
        {"by": list(_BY_FRAME), "checkFunc": _ALWAYS, "recycle": False},
        args,
        kwargs,
    )
    by = match_arg(bound["by"], _BY_FRAME)
    length = len(obj.names) if by == "column" else obj.nrow
    return Iter(
        ["dataframeiter", "iter"],
        state=State(i=0, obj=obj),
        by=by,
        length=length,
        checkFunc=_resolve_check(bound["checkFunc"]),
        recycle=bound["recycle"],
    )


def _iter_function(obj, *args, **kwargs):
    bound = _bind(
        ("checkFunc", "recycle"),
        {"checkFunc": _ALWAYS, "recycle": False},
        args,
        kwargs,
    )
    return Iter(
        ["funiter", "iter"],
        state=State(i=0, fun=obj),
        args=_has_formals(obj),
        checkFunc=_resolve_check(bound["checkFunc"]),
        recycle=bound["recycle"],
    )


def iter(obj=_MISSING, *args, **kwargs):
    """Build an iterator over a vector, matrix, data frame, function, or iterator.

    Calling it on an iterator returns that same object. ``by`` is ``column``,
    ``cell``, or ``row`` for a matrix, and ``column`` or ``row`` for a data
    frame. ``chunksize`` groups matrix columns or rows. ``checkFunc`` drops a
    value when it returns false. ``recycle`` starts again after the last value.
    """
    if obj is _MISSING:
        raise IteratorError("argument \"obj\" is missing, with no default")
    kind = _kind(obj)
    if kind == "iter":
        return _iter_self(obj, *args, **kwargs)
    if kind == "matrix":
        return _iter_matrix(obj, *args, **kwargs)
    if kind == "data.frame":
        return _iter_frame(obj, *args, **kwargs)
    if kind == "function":
        return _iter_function(obj, *args, **kwargs)
    return _iter_default(obj, *args, **kwargs)


def _count_value(count):
    if isinstance(count, bool) or count is None:
        raise IteratorError("count must be a numeric value")
    if isinstance(count, (int, float)):
        return count
    if isinstance(count, (list, tuple)):
        if (
            len(count) == 1
            and not isinstance(count[0], bool)
            and isinstance(count[0], (int, float))
        ):
            return count[0]
        raise IteratorError("count must be a numeric value")
    if isinstance(count, np.ndarray) and count.dtype.kind in "iuf" and count.size == 1:
        return _scalar(np.ravel(count)[0])
    raise IteratorError("count must be a numeric value")


def _below(index, limit):
    if isinstance(limit, float) and math.isnan(limit):
        raise IteratorError("missing value where TRUE/FALSE needed")
    return index < limit


def icount(count=_MISSING):
    """Count from 1 through ``count``. A missing ``count`` does not stop.

    ``NULL``, a non-number, and a count whose length is not 1 all stop with
    ``count must be a numeric value``. The counter is an integer that starts
    at 0, and each step adds 1 while it is still below ``count``.
    """
    forever = count is _MISSING
    limit = None if forever else _count_value(count)
    index = 0

    def next_el():
        nonlocal index
        if forever or _below(index, limit):
            index = index + 1
            return index
        raise IteratorError("StopIteration")

    return Iter(["abstractiter", "iter"], nextElem=next_el)
