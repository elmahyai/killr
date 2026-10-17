"""foreach, %do%, and times from foreach 1.5.2.

``foreach`` builds the loop. ``do`` is ``%do%``: it walks the iterators with
``iterators.core`` and combines the values in order. ``times`` repeats an
expression by counting with ``icount``. A Python callable is the R
expression; a value that is not callable is a constant expression. Loop
variables are passed by name. Unnamed iterators are positional arguments.
"""

from __future__ import annotations

import inspect
import math
import re
import sys
from pathlib import Path

import numpy as np


_ITERATORS = Path(__file__).resolve().parents[2] / "iterators"
if _ITERATORS.is_dir():
    _iterators_path = str(_ITERATORS)
    if _iterators_path not in sys.path:
        sys.path.insert(0, _iterators_path)

from iterators.core import IteratorError, icount, iter, match_arg, nextElem


_OLD = (
    "COMBINE",
    "INIT",
    "INORDER",
    "MULTICOMBINE",
    "MAXCOMBINE",
    "ERRORHANDLING",
    "PACKAGES",
    "VERBOSE",
    "EXPORT",
    "NOEXPORT",
    "LOADFACTOR",
    "CHUNKSIZE",
)
_OPTIONS = (
    "combine",
    "init",
    "final",
    "inorder",
    "multicombine",
    "maxcombine",
    "errorhandling",
    "packages",
    "export",
    "noexport",
    "verbose",
)
_MISSING = object()


class ForeachError(Exception):
    """An R ``stop`` from this package."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class TaskError:
    """An error object returned by one task, as ``tryCatch`` returns it."""

    def __init__(self, message):
        self.message = message


class RList(list):
    """An R list. A plain list is an atomic vector."""


class RMatrix:
    """A matrix with the dimnames ``cbind`` and ``rbind`` attach."""

    def __init__(self, data, rownames=None, colnames=None):
        self.data = np.asarray(data)
        self.rownames = rownames
        self.colnames = colnames

    def __repr__(self):
        return "RMatrix(" + repr(self.data) + ")"


class Foreach:
    """The object ``foreach`` returns. ``do`` is what evaluates it."""

    def __init__(self, **fields):
        for key, value in fields.items():
            setattr(self, key, value)

    def __repr__(self):
        return "Foreach(" + ", ".join(self.argnames) + ")"


class _State:
    def __init__(self):
        self.stopped = False
        self.num_values = 0
        self.num_results = 0
        self.accum = None
        self.first_time = True
        self.results = {}
        self.buffered = []
        self.buf_off = 0
        self.nbuf = 0
        self.error_value = None
        self.error_index = -1


class _IForeach:
    def __init__(self, **fields):
        for key, value in fields.items():
            setattr(self, key, value)


def _message(exc):
    if isinstance(exc, (ForeachError, IteratorError, TaskError)):
        return exc.message
    return str(exc)


def _is_r_logical(value):
    if isinstance(value, bool):
        return True
    if isinstance(value, (list, tuple)) and all(isinstance(item, bool) for item in value):
        return True
    return False


def _is_r_character(value):
    if isinstance(value, str):
        return True
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return True
    return False


def _is_r_numeric(value):
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, np.ndarray) and value.dtype.kind in "iuf":
        return True
    if isinstance(value, (list, tuple)):
        return all(
            _is_r_numeric(item) and not isinstance(item, (list, tuple, np.ndarray))
            for item in value
        )
    return False


def _r_length(value):
    if isinstance(value, (list, tuple, np.ndarray)):
        return len(value) if not isinstance(value, np.ndarray) else int(value.size)
    return 1


def _one_number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray) and value.dtype.kind in "iuf" and value.size == 1:
        return value.reshape(-1)[0].item()
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return _one_number(value[0])
    return None


def _integral(number):
    if isinstance(number, float) and number.is_integer() and abs(number) < 2**53:
        return int(number)
    return number


def _condition_true(value):
    """R ``if`` on a flag: NA, length zero, and length greater than one."""
    if isinstance(value, np.ndarray):
        if value.size == 0:
            raise ForeachError("argument is of length zero")
        if value.size > 1:
            raise ForeachError("the condition has length > 1")
        value = value.reshape(-1)[0].item()
    elif isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ForeachError("argument is of length zero")
        if len(value) > 1:
            raise ForeachError("the condition has length > 1")
        value = value[0]
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise ForeachError("missing value where TRUE/FALSE needed")
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        if math.isnan(number):
            raise ForeachError("missing value where TRUE/FALSE needed")
        return number != 0
    raise ForeachError("argument is not interpretable as logical")


def _is_function(value):
    return callable(value) and not isinstance(value, type)


def _py_num(value):
    if isinstance(value, np.generic):
        return value.item()
    return value


def _atomic_items(value):
    if isinstance(value, str) or isinstance(value, TaskError):
        return [value]
    if isinstance(value, RMatrix):
        return [_py_num(item) for item in np.ravel(value.data, order="F")]
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return [_py_num(value)]
        return [_py_num(item) for item in np.ravel(value, order="F")]
    if isinstance(value, (list, tuple)) and not isinstance(value, RList):
        return [_py_num(item) if not isinstance(item, str) else item for item in value]
    if isinstance(value, (np.integer, np.floating)):
        return [_py_num(value)]
    return [value]


def _promote(flat):
    if any(isinstance(item, str) for item in flat):
        return [str(item) for item in flat]
    if any(isinstance(item, float) for item in flat):
        return [float(item) for item in flat]
    return [int(item) for item in flat]


def _c(*args):
    """R ``c``. A list splices its elements; atomic vectors flatten."""
    if any(isinstance(arg, RList) for arg in args):
        out = RList()
        for arg in args:
            if isinstance(arg, RList):
                out.extend(arg)
            else:
                out.extend(_atomic_items(arg))
        return out
    flat = []
    for arg in args:
        flat.extend(_atomic_items(arg))
    return _promote(flat)


def _defcombine(accum, *rest):
    return _c(accum, RList(rest))


def _add(*args):
    if len(args) < 1 or len(args) > 2:
        raise ForeachError("operator needs one or two arguments")
    if len(args) == 1:
        return args[0]
    return args[0] + args[1]


def _mul(*args):
    if len(args) < 1 or len(args) > 2:
        raise ForeachError("operator needs one or two arguments")
    if len(args) == 1:
        return args[0]
    return args[0] * args[1]


def _flat_array(value):
    if isinstance(value, np.ndarray):
        return np.ravel(value, order="F")
    if isinstance(value, (list, tuple)) and not isinstance(value, RList):
        return np.asarray(value)
    return np.asarray([value])


def _block(value, name, axis):
    if isinstance(value, RMatrix):
        data = value.data
        if axis == 1:
            labels = list(value.colnames) if value.colnames is not None else [None] * data.shape[1]
        else:
            labels = list(value.rownames) if value.rownames is not None else [None] * data.shape[0]
        return data, labels, value.rownames, value.colnames
    if isinstance(value, np.ndarray) and value.ndim == 2:
        if axis == 1:
            return value, [None] * value.shape[1], None, None
        return value, [None] * value.shape[0], None, None
    flat = _flat_array(value)
    if axis == 1:
        return flat.reshape(-1, 1), [name], None, None
    return flat.reshape(1, -1), [name], None, None


def _finish_bind(data, rownames, colnames):
    rows_blank = rownames is None or all(name is None for name in rownames)
    cols_blank = colnames is None or all(name is None for name in colnames)
    if rows_blank and cols_blank:
        return data
    return RMatrix(
        data,
        None if rows_blank else rownames,
        None if cols_blank else colnames,
    )


def _cbind(values, names):
    blocks = []
    colnames = []
    rownames = None
    for value, name in zip(values, names):
        block, labels, rows, _cols = _block(value, name, 1)
        blocks.append(block)
        colnames.extend(labels)
        if rownames is None and rows is not None:
            rownames = rows
    return _finish_bind(np.concatenate(blocks, axis=1), rownames, colnames)


def _rbind(values, names):
    blocks = []
    rownames = []
    colnames = None
    for value, name in zip(values, names):
        block, labels, _rows, cols = _block(value, name, 0)
        blocks.append(block)
        rownames.extend(labels)
        if colnames is None and cols is not None:
            colnames = cols
    return _finish_bind(np.concatenate(blocks, axis=0), rownames, colnames)


_BY_NAME = {
    "c": _c,
    "cbind": _cbind,
    "rbind": _rbind,
    "+": _add,
    "*": _mul,
}


def _match_fun(fun):
    if isinstance(fun, str):
        found = _BY_NAME.get(fun)
        if found is None:
            raise ForeachError(f"object '{fun}' of mode 'function' was not found")
        return found
    if _is_function(fun):
        return fun
    raise ForeachError(f"'{fun}' is not a function, character or symbol")


def _check_maxcombine(value):
    if not _is_r_numeric(value):
        raise ForeachError(".maxcombine must be a numeric value >= 2")
    length = _r_length(value)
    if length > 1:
        raise ForeachError(".maxcombine must be a numeric value >= 2")
    if length == 0:
        raise ForeachError("argument is of length zero")
    number = _one_number(value)
    if isinstance(number, float) and math.isnan(number):
        raise ForeachError("missing value where TRUE/FALSE needed")
    if number < 2:
        raise ForeachError(".maxcombine must be a numeric value >= 2")
    return _integral(number)


def _clone(value):
    if isinstance(value, RList):
        return RList(value)
    if isinstance(value, list):
        return list(value)
    return value


def _take(kwargs, name):
    dotted = "." + name
    if name in kwargs and dotted in kwargs:
        raise ForeachError(
            f'formal argument "{name}" matched by multiple actual arguments'
        )
    if dotted in kwargs:
        return kwargs.pop(dotted), False
    if name in kwargs:
        return kwargs.pop(name), False
    return _MISSING, True


def _logical_flag(value, label):
    if not _is_r_logical(value) or _r_length(value) > 1:
        raise ForeachError(f".{label} must be a logical value")
    if isinstance(value, (list, tuple)):
        return value[0] if len(value) == 1 else value
    return value


def foreach(*args, **kwargs):
    """Build a foreach loop.

    Named arguments are the loop variables. Positional arguments are unnamed
    iterators and only set how many times the loop runs. ``combine`` is R's
    ``.combine``: a function, or ``"c"``, ``"cbind"``, ``"rbind"``, ``"+"``,
    or ``"*"``. The default combine returns a list. ``init`` is the first
    accumulator value. ``final`` is called on that accumulator at the end.
    ``inorder``, ``multicombine``, ``maxcombine``, and ``errorhandling``
    follow the R arguments. ``errorhandling`` is ``"stop"``, ``"remove"``,
    or ``"pass"``.
    """
    supplied = {}
    missing = {}
    for name in _OPTIONS:
        supplied[name], missing[name] = _take(kwargs, name)

    if missing["combine"]:
        if not missing["init"]:
            raise ForeachError(
                "if .init is specified, then .combine must also be specified"
            )
        combine_fun = _defcombine
        has_init = True
        init = RList()
    else:
        combine_fun = _match_fun(supplied["combine"])
        if missing["init"]:
            has_init = False
            init = None
        else:
            has_init = True
            init = supplied["init"]
            if isinstance(init, list) and not isinstance(init, RList):
                init = RList(init)

    if missing["multicombine"]:
        multicombine = False
    else:
        multicombine = supplied["multicombine"]
    if missing["multicombine"] and combine_fun in (_cbind, _rbind, _c, _defcombine):
        multicombine = True

    final = None if missing["final"] else supplied["final"]
    if final is not None and not _is_function(final):
        raise ForeachError(".final must be a function")

    inorder = True if missing["inorder"] else supplied["inorder"]
    inorder = _logical_flag(inorder, "inorder")

    multicombine = _logical_flag(multicombine, "multicombine")

    if missing["maxcombine"]:
        maxcombine = 100 if _condition_true(multicombine) else 2
    else:
        maxcombine = supplied["maxcombine"]
    maxcombine = _check_maxcombine(maxcombine)

    if missing["errorhandling"]:
        errorhandling = "stop"
    else:
        errorhandling = supplied["errorhandling"]
        if not _is_r_character(errorhandling):
            raise ForeachError(".errorhandling must be a character string")

    packages = None if missing["packages"] else supplied["packages"]
    if packages is not None and not _is_r_character(packages):
        raise ForeachError(".packages must be a character vector")
    export = None if missing["export"] else supplied["export"]
    if export is not None and not _is_r_character(export):
        raise ForeachError(".export must be a character vector")
    noexport = None if missing["noexport"] else supplied["noexport"]
    if noexport is not None and not _is_r_character(noexport):
        raise ForeachError(".noexport must be a character vector")

    verbose = False if missing["verbose"] else supplied["verbose"]
    verbose = _logical_flag(verbose, "verbose")

    specified = []
    if not missing["errorhandling"]:
        specified.append("errorHandling")
    if not missing["verbose"]:
        specified.append("verbose")

    if len(args) == 0 and len(kwargs) == 0:
        raise ForeachError("no iteration arguments specified")

    names = [""] * len(args)
    values = list(args)
    options = {}
    unrecognized = []
    for key, value in kwargs.items():
        match = re.fullmatch(r"\.options\.([A-Za-z][A-Za-z]*)", key)
        if match:
            options[match.group(1)] = value
            continue
        if key.startswith("."):
            unrecognized.append(key)
            continue
        names.append(key)
        values.append(value)
    if unrecognized:
        raise ForeachError(
            "unrecognized argument(s): " + ", ".join(unrecognized)
        )
    old = [name for name in names if name in _OLD]
    if old:
        raise ForeachError("old style argument(s) specified: " + ", ".join(old))

    if not missing["errorhandling"]:
        try:
            errorhandling = match_arg(errorhandling, ("stop", "remove", "pass"))
        except IteratorError as exc:
            raise ForeachError(exc.message) from None

    return Foreach(
        values=values,
        argnames=names,
        combine_fun=combine_fun,
        has_init=has_init,
        init=init,
        final=final,
        in_order=inorder,
        multicombine=multicombine,
        max_combine=maxcombine,
        error_handling=errorhandling,
        packages=packages,
        export=export,
        noexport=noexport,
        options=options,
        verbose=verbose,
        specified=specified,
    )


def _verbose(flag, text):
    if _condition_true(flag):
        sys.stdout.write(text)


def _invoke(fun, accum, tags, state, first):
    values = [state.results[tag] for tag in tags]
    names = [f"result.{tag}" for tag in tags]
    if fun is _cbind or fun is _rbind:
        if first:
            return fun(values, names)
        return fun([accum, *values], [None, *names])
    if first:
        return fun(*values)
    return fun(accum, *values)


def _leading(buffered):
    for index, item in enumerate(buffered):
        if item is None:
            return index
    raise ForeachError("is.na(n) is not TRUE")


def _consume(obj, count, in_order):
    state = obj.state
    chunk = state.buffered[:count]
    positive = [tag for tag in chunk if tag is not None and tag > 0]
    consumed = [abs(tag) for tag in chunk if tag is not None]
    if positive:
        _verbose(obj.verbose, "calling combine function\n")
        if state.first_time:
            state.first_time = False
            if len(positive) == 1:
                state.accum = state.results[positive[0]]
            else:
                state.accum = _invoke(obj.combine_fun, None, positive, state, True)
        else:
            state.accum = _invoke(obj.combine_fun, state.accum, positive, state, False)
    for tag in consumed:
        state.results.pop(tag, None)
    if in_order:
        state.buffered = state.buffered[count:] + [None] * count
        state.buf_off += count
    else:
        for index in range(count):
            state.buffered[index] = None
        state.nbuf = 0


def _call_combine(obj, status):
    in_order = _condition_true(obj.in_order)
    if in_order:
        while True:
            needed = obj.max_combine if obj.state.first_time else obj.max_combine - 1
            leading = _leading(obj.state.buffered)
            count = min(leading, needed)
            if count == needed or (status and count > 0):
                _consume(obj, int(count), True)
            else:
                break
        return
    needed = obj.max_combine if obj.state.first_time else obj.max_combine - 1
    if obj.state.nbuf > needed:
        raise ForeachError("obj$state$nbuf <= needed is not TRUE")
    if obj.state.nbuf == needed or (status and obj.state.nbuf > 0):
        _consume(obj, int(obj.state.nbuf), False)


def _complete(obj):
    _verbose(
        obj.verbose,
        "numValues: %d, numResults: %d, stopped: %s\n"
        % (
            obj.state.num_values,
            obj.state.num_results,
            "TRUE" if obj.state.stopped else "FALSE",
        ),
    )
    if not obj.state.stopped:
        return False
    return obj.state.num_results == obj.state.num_values


def _accumulate(obj, result, tag):
    state = obj.state
    state.num_results += 1
    if state.num_results > state.num_values:
        raise ForeachError("numResults <= numValues is not TRUE")
    is_error = isinstance(result, TaskError)
    if (
        is_error
        and state.error_value is None
        and obj.error_handling in ("stop", "remove")
    ):
        _verbose(obj.verbose, "accumulate got an error result\n")
        state.error_value = result
        state.error_index = tag
    status = _complete(obj)
    state.results[tag] = result
    if _condition_true(obj.in_order):
        ibuf = tag - state.buf_off
    else:
        state.nbuf += 1
        ibuf = state.nbuf
    while ibuf >= len(state.buffered):
        state.buffered.extend([None] * len(state.buffered))
    dropped = is_error and obj.error_handling in ("stop", "remove")
    state.buffered[ibuf - 1] = -tag if dropped else tag
    _call_combine(obj, status)
    _verbose(obj.verbose, "returning status %s\n" % ("TRUE" if status else "FALSE"))
    return status


def _make_accum(it):
    def accumulator(results, tags):
        for result, tag in zip(results, tags):
            _verbose(it.verbose, "got results for task %d\n" % tag)
            _accumulate(it, result, tag)

    return accumulator


def _pull(obj):
    pairs = list(zip(obj.argnames, obj.iargs))
    if any(name == "" for name, _it in pairs):
        for name, iterator in pairs:
            if name == "":
                nextElem(iterator)
        named = [(name, iterator) for name, iterator in pairs if name != ""]
        if not named:
            return {}
        return {name: nextElem(iterator) for name, iterator in named}
    return {name: nextElem(iterator) for name, iterator in pairs}


def _next_iforeach(obj):
    try:
        element = _pull(obj)
    except Exception as exc:
        message = _message(exc)
        if message == "StopIteration":
            obj.state.stopped = True
            if _complete(obj):
                _call_combine(obj, True)
        raise ForeachError(message) from None
    obj.state.num_values += 1
    return element


def _prepare(value):
    """A bare number or string is a length-1 vector, as in R."""
    if isinstance(value, (bool, int, float, str)):
        return [value]
    if isinstance(value, (np.integer, np.floating)):
        return [value.item()]
    return value


def _iter_foreach(obj):
    state = _State()
    width = int(2 * obj.max_combine)
    state.buffered = [None] * width
    if obj.has_init:
        state.accum = _clone(obj.init)
        state.first_time = False
    else:
        state.accum = None
        state.first_time = True
    return _IForeach(
        state=state,
        iargs=[iter(_prepare(value)) for value in obj.values],
        argnames=list(obj.argnames),
        combine_fun=obj.combine_fun,
        in_order=obj.in_order,
        max_combine=obj.max_combine,
        final=obj.final,
        error_handling=obj.error_handling,
        verbose=obj.verbose,
    )


def _call_user(ex, args):
    if not callable(ex):
        return ex
    if not args:
        return ex()
    try:
        signature = inspect.signature(ex)
    except (TypeError, ValueError):
        return ex(**args)
    params = list(signature.parameters.values())
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params):
        return ex(**args)
    accepted = {
        param.name
        for param in params
        if param.kind
        in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    }
    if not accepted:
        return ex()
    return ex(**{key: value for key, value in args.items() if key in accepted})


def _report_combine_error(exc):
    sys.stdout.write("error calling combine function:\n")
    sys.stdout.write(repr(exc) + "\n")


def _get_result(it):
    if it.final is None:
        return it.state.accum
    return it.final(it.state.accum)


def do(obj, ex):
    """Evaluate ``ex`` once per step of ``obj``, in order.

    This is ``%do%``. ``ex`` is a callable of the loop variables, or a
    constant. The result is a list unless ``combine`` says otherwise.
    ``"stop"`` raises ``task <n> failed``. ``"remove"`` drops a failed task.
    ``"pass"`` keeps the error object in the result.
    """
    if not isinstance(obj, Foreach):
        raise ForeachError("obj must be a foreach object")
    it = _iter_foreach(obj)
    accumulator = _make_accum(it)
    index = 1
    try:
        while True:
            args = _next_iforeach(it)
            _verbose(obj.verbose, "evaluation # %d:\n" % index)
            try:
                result = _call_user(ex, args)
            except Exception as exc:
                result = TaskError(_message(exc))
            _verbose(obj.verbose, "result of evaluating expression:\n")
            try:
                accumulator([result], [index])
            except ForeachError as exc:
                if exc.message == "StopIteration":
                    raise
                _report_combine_error(exc)
            except Exception as exc:
                _report_combine_error(exc)
            index += 1
    except ForeachError as exc:
        if exc.message != "StopIteration":
            raise ForeachError(exc.message) from None
    if obj.error_handling == "stop" and it.state.error_value is not None:
        failed = it.state.error_value
        raise ForeachError(
            'task %d failed - "%s"' % (it.state.error_index, failed.message)
        )
    return _get_result(it)


def times(n):
    """Repeat an expression ``n`` times.

    ``n`` has to be one number. The loop variable is unnamed, and the
    results are combined with ``c``.
    """
    if isinstance(n, bool) or not _is_r_numeric(n) or _r_length(n) != 1:
        raise ForeachError("n must be a numeric value")
    return foreach(icount(_one_number(n)), combine="c")
