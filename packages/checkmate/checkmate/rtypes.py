"""R values for checkmate: storage mode, missingness, and the C predicates."""

from __future__ import annotations

import inspect
import math
import os
import sys
from collections.abc import Callable, Mapping, Sequence

INT_MIN = -2147483648
INT_MAX = 2147483647
DEFAULT_TOL = math.sqrt(sys.float_info.epsilon)


class Missing:
    """R's NA. Distinct from a plain NaN."""

    def __repr__(self) -> str:
        return "NA"

    def __hash__(self) -> int:
        return 0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Missing)


NA = Missing()


class CheckError(Exception):
    """An R stop() from checkmate, message unchanged."""


class _Null:
    mode = "null"
    data: tuple = ()
    names = None
    dim = None
    klass: tuple[str, ...] = ()
    levels = None
    ordered = False
    tzone = None
    rownames = None
    dimnames = None

    def __len__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "NULL"

    def __iter__(self):
        return iter(())


NULL = _Null()


class Vec:
    """Atomic vector, list, matrix, array, factor, Date, or POSIXct."""

    def __init__(
        self,
        mode: str,
        data: Sequence,
        names: Sequence[str | Missing] | None = None,
        dim: Sequence[int] | None = None,
        klass: Sequence[str] | None = None,
        levels: Sequence[str] | None = None,
        ordered: bool = False,
        tzone: str | None = None,
        rownames: Sequence | None = None,
        dimnames: Sequence | None = None,
        nrows: int | None = None,
    ) -> None:
        self.mode = mode
        self.data = list(data)
        self.names = None if names is None else list(names)
        self.dim = None if dim is None else tuple(int(item) for item in dim)
        self.klass = tuple(klass or ())
        self.levels = None if levels is None else list(levels)
        self.ordered = ordered
        self.tzone = tzone
        self.rownames = None if rownames is None else list(rownames)
        self.dimnames = None if dimnames is None else list(dimnames)
        self.nrows = nrows

    def __len__(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"{self.mode}({self.data!r})"


class Environment:
    def __init__(self, bindings: Mapping | None = None) -> None:
        self.mode = "environment"
        self.bindings = dict(bindings or {})
        self.klass: tuple[str, ...] = ()
        self.names = None
        self.dim = None
        self.data: list = []

    def __len__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "environment()"


class Formula:
    def __init__(self, text: str = "") -> None:
        self.mode = "language"
        self.text = text
        self.klass = ("formula",)
        self.names = None
        self.dim = None
        self.data: list = []

    def __repr__(self) -> str:
        return self.text or "formula()"


class Function:
    def __init__(self, formals: Sequence[str], impl: Callable | None = None) -> None:
        self.mode = "function"
        self.formals = list(formals)
        self.impl = impl
        self.klass: tuple[str, ...] = ()
        self.names = None
        self.dim = None
        self.data: list = []

    @classmethod
    def from_callable(cls, fn: Callable) -> Function:
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            return cls([], fn)
        names = []
        for name, param in sig.parameters.items():
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                names.append("...")
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                continue
            else:
                names.append(name)
        return cls(names, fn)


def logical(values, names=None) -> Vec:
    return Vec("logical", _atoms(values, "logical"), names)


def integer(values, names=None) -> Vec:
    return Vec("integer", _atoms(values, "integer"), names)


def double(values, names=None) -> Vec:
    return Vec("double", _atoms(values, "double"), names)


def character(values, names=None) -> Vec:
    return Vec("character", _atoms(values, "character"), names)


def complex_(values, names=None) -> Vec:
    return Vec("complex", _atoms(values, "complex"), names)


def raw(values, names=None) -> Vec:
    if isinstance(values, (bytes, bytearray)):
        data = list(values)
    else:
        data = list(values)
    return Vec("raw", data, names)


def rlist(values, names=None) -> Vec:
    return Vec("list", [wrap(item) for item in values], names)


def factor(values, levels: Sequence[str] | None = None, ordered: bool = False, names=None) -> Vec:
    labels = list(levels) if levels is not None else list(dict.fromkeys(
        item for item in values if item is not NA and item is not None
    ))
    codes = []
    for item in values:
        if item is NA or item is None:
            codes.append(NA)
        else:
            text = item if isinstance(item, str) else str(item)
            if text not in labels:
                raise CheckError(f"factor level '{text}' is not in levels")
            codes.append(labels.index(text) + 1)
    klass = ("ordered", "factor") if ordered else ("factor",)
    return Vec("integer", codes, names, klass=klass, levels=labels, ordered=ordered)


def matrix(values, nrow: int, ncol: int | None = None, mode: str = "double",
           rownames=None, colnames=None) -> Vec:
    data = list(values)
    if ncol is None:
        if nrow == 0:
            ncol = 0
        elif len(data) % nrow:
            raise CheckError("data length is not a multiple of nrow")
        else:
            ncol = len(data) // nrow
    dimnames = [rownames, colnames]
    if rownames is None and colnames is None:
        dimnames = None
    return Vec(mode, data, dim=(nrow, ncol), dimnames=dimnames)


def array(values, dim: Sequence[int], mode: str = "double") -> Vec:
    return Vec(mode, list(values), dim=tuple(dim))


def data_frame(columns: Mapping[str, Vec], rownames: Sequence | None = None) -> Vec:
    cols = []
    names = []
    nrows = None
    for name, column in columns.items():
        wrapped = wrap(column)
        if not isinstance(wrapped, Vec):
            wrapped = wrap(column)
        cols.append(wrapped)
        names.append(name)
        nrows = len(wrapped.data) if nrows is None else nrows
    if nrows is None:
        nrows = 0 if rownames is None else len(rownames)
    if rownames is None:
        rownames = [str(i) for i in range(1, (nrows or 0) + 1)]
    return Vec("list", cols, names=names, klass=("data.frame",), rownames=list(rownames), nrows=nrows)


def data_table(columns: Mapping[str, Vec], key=None, index=None, rownames: Sequence | None = None) -> Vec:
    """A data frame that also inherits data.table, with optional keys."""
    frame = data_frame(columns, rownames)
    frame.klass = ("data.table", "data.frame")
    frame.dt_key = None if key is None else list(key)
    frame.dt_index = None if index is None else list(index)
    return frame


def as_tibble(columns: Mapping[str, Vec], rownames: Sequence | None = None) -> Vec:
    """A data frame that also inherits tbl_df and tbl."""
    frame = data_frame(columns, rownames)
    frame.klass = ("tbl_df", "tbl", "data.frame")
    return frame


class R6:
    """An R6 object: public and private slots, plus an optional clone method."""

    def __init__(self, classes, public=None, private=None, cloneable: bool = True):
        names = [classes] if isinstance(classes, str) else list(classes)
        if "R6" not in names:
            names.append("R6")
        self.r_class = tuple(names)
        self.public = dict(public or {})
        self.private = dict(private or {})
        self.cloneable = cloneable
        if cloneable:
            self.public.setdefault("clone", lambda deep=False: self)

    def __repr__(self) -> str:
        return f"R6({self.r_class[0]})"


def posixct(values, tz: str | None = None, names=None) -> Vec:
    return Vec("double", _atoms(values, "double"), names, klass=("POSIXct", "POSIXt"), tzone=tz)


def date(values, names=None) -> Vec:
    return Vec("double", _atoms(values, "double"), names, klass=("Date",))


def formula(text: str) -> Formula:
    return Formula(text)


def environment(bindings: Mapping | None = None) -> Environment:
    return Environment(bindings)


def _wrap_sequence(values) -> Vec:
    if not values:
        return Vec("list", [])
    kinds = []
    for item in values:
        if item is NA or isinstance(item, Missing):
            kinds.append("na")
        elif type(item) is bool:
            kinds.append("logical")
        elif type(item) is int:
            kinds.append("integer")
        elif type(item) is float:
            kinds.append("double")
        elif type(item) is str:
            kinds.append("character")
        elif type(item) is complex:
            kinds.append("complex")
        else:
            kinds.append("other")
    concrete = {kind for kind in kinds if kind != "na"}
    if len(concrete) == 1 and "other" not in concrete:
        mode = concrete.pop()
        return Vec(mode, _atoms(values, mode))
    return Vec("list", [wrap(item) for item in values])


def _atoms(values, mode: str) -> list:
    if isinstance(values, Vec):
        return list(values.data)
    if isinstance(values, (str, bytes)) and mode != "character":
        values = [values]
    elif not isinstance(values, (list, tuple)):
        values = [values]
    out = []
    for item in values:
        if item is NA or isinstance(item, Missing):
            out.append(NA)
        elif mode == "logical":
            out.append(bool(item) if item is not NA else NA)
        elif mode == "integer":
            out.append(int(item) if item is not NA else NA)
        elif mode == "double":
            out.append(float(item) if item is not NA else NA)
        elif mode == "character":
            out.append(item if item is NA else str(item))
        elif mode == "complex":
            out.append(item if item is NA else complex(item))
        else:
            out.append(item)
    return out


def wrap(value):
    if isinstance(value, (Vec, _Null, Environment, Formula, Function)):
        return value
    if value is None:
        return NULL
    if value is NA or isinstance(value, Missing):
        return Vec("logical", [NA])
    if type(value) is bool:
        return Vec("logical", [value])
    if type(value) is int:
        return Vec("integer", [value])
    if type(value) is float:
        return Vec("double", [value])
    if type(value) is str:
        return Vec("character", [value])
    if type(value) is complex:
        return Vec("complex", [value])
    if isinstance(value, (bytes, bytearray)):
        return Vec("raw", list(value))
    if isinstance(value, (list, tuple)):
        return _wrap_sequence(value)
    if callable(value):
        return Function.from_callable(value)
    if getattr(value, "r_class", None):
        return value
    raise CheckError(f"cannot interpret {type(value).__name__} as an R value")


def is_null(value) -> bool:
    return value is None or isinstance(value, _Null) or (isinstance(value, Vec) and value.mode == "null")


def xlength(value) -> int:
    value = value if isinstance(value, (Vec, _Null, Environment, Formula, Function)) else wrap(value)
    if is_null(value):
        return 0
    return len(value.data)


def is_na_scalar(item, mode: str) -> bool:
    if item is NA or isinstance(item, Missing):
        return True
    if mode == "double" and isinstance(item, float) and math.isnan(item):
        return True
    if mode == "complex" and isinstance(item, complex) and (math.isnan(item.real) or math.isnan(item.imag)):
        return True
    return False


def is_nan_scalar(item, mode: str) -> bool:
    if item is NA or isinstance(item, Missing):
        return False
    if mode == "double" and isinstance(item, float) and math.isnan(item):
        return True
    if mode == "complex" and isinstance(item, complex) and (
        (isinstance(item.real, float) and math.isnan(item.real) and item.real is not NA)
        or (isinstance(item.imag, float) and math.isnan(item.imag))
    ):
        if isinstance(item.real, float) and math.isnan(item.real):
            return True
        if isinstance(item.imag, float) and math.isnan(item.imag):
            return True
    return False


def is_infinite(item) -> bool:
    return isinstance(item, float) and math.isinf(item)


def inherits(value, classes) -> bool:
    if isinstance(classes, str):
        classes = [classes]
    have = rclass(value)
    return any(name in have for name in classes)


def inherits_which(value, classes: Sequence[str]) -> list[int]:
    have = list(rclass(value))
    found = []
    for name in classes:
        found.append(have.index(name) + 1 if name in have else 0)
    return found


def rclass(value) -> tuple[str, ...]:
    if getattr(value, "r_class", None) and not isinstance(value, (Vec, _Null, Environment, Formula, Function)):
        return tuple(value.r_class)
    value = value if isinstance(value, (Vec, _Null, Environment, Formula, Function)) else wrap(value)
    if is_null(value):
        return ("NULL",)
    if isinstance(value, Vec) and value.klass:
        return value.klass
    if isinstance(value, Vec) and value.dim is not None and value.mode != "list":
        if len(value.dim) == 2:
            return ("matrix", "array")
        return ("array",)
    mode = getattr(value, "mode", None)
    return {
        "double": ("numeric",),
        "integer": ("integer",),
        "logical": ("logical",),
        "character": ("character",),
        "complex": ("complex",),
        "raw": ("raw",),
        "list": ("list",),
        "function": ("function",),
        "environment": ("environment",),
        "language": ("language",),
    }.get(mode, (mode or "unknown",))


def guess_type(value) -> str:
    if getattr(value, "r_class", None) and not isinstance(value, (Vec, _Null, Environment, Formula, Function)):
        return "/".join(value.r_class)
    value = value if isinstance(value, (Vec, _Null, Environment, Formula, Function)) else wrap(value)
    if is_null(value):
        return "NULL"
    if isinstance(value, Vec) and value.klass:
        if len(value.klass) == 1:
            return value.klass[0]
        return "/".join(value.klass)
    if isinstance(value, Vec) and value.dim is not None and value.mode != "list":
        return "matrix" if len(value.dim) == 2 else "array"
    return {
        "logical": "logical",
        "integer": "integer",
        "double": "double",
        "complex": "complex",
        "character": "character",
        "raw": "raw",
        "list": "list",
        "function": "function",
        "environment": "environment",
        "language": "language",
        "null": "NULL",
    }.get(getattr(value, "mode", ""), "unknown")


def is_atomic_mode(value) -> bool:
    return isinstance(value, Vec) and value.mode in {"logical", "integer", "double", "complex", "character", "raw"}


def is_class_logical(value) -> bool:
    return isinstance(value, Vec) and value.mode == "logical"


def is_class_integer(value) -> bool:
    return isinstance(value, Vec) and value.mode == "integer"


def is_class_double(value) -> bool:
    return isinstance(value, Vec) and value.mode == "double"


def is_class_numeric(value) -> bool:
    if not isinstance(value, Vec):
        return False
    if value.mode == "double":
        return True
    if value.mode == "integer" and "factor" not in value.klass:
        return True
    return False


def is_class_complex(value) -> bool:
    return isinstance(value, Vec) and value.mode == "complex"


def is_class_string(value) -> bool:
    return isinstance(value, Vec) and value.mode == "character"


def is_class_factor(value) -> bool:
    return isinstance(value, Vec) and "factor" in value.klass


def is_class_atomic(value) -> bool:
    return is_null(value) or is_atomic_mode(value)


def is_class_atomic_vector(value) -> bool:
    return is_atomic_mode(value) and (not isinstance(value, Vec) or value.dim is None)


def is_class_list(value) -> bool:
    return isinstance(value, Vec) and value.mode == "list" and "data.frame" not in value.klass


def is_class_matrix(value) -> bool:
    return isinstance(value, Vec) and value.dim is not None and len(value.dim) == 2 and value.mode != "list"


def is_class_array(value) -> bool:
    return isinstance(value, Vec) and value.dim is not None and value.mode != "list"


def is_class_frame(value) -> bool:
    return isinstance(value, Vec) and "data.frame" in value.klass


def is_class_environment(value) -> bool:
    return isinstance(value, Environment)


def is_class_posixct(value) -> bool:
    return is_class_numeric(value) and isinstance(value, Vec) and "POSIXct" in value.klass


def is_class_raw(value) -> bool:
    return isinstance(value, Vec) and value.mode == "raw"


def is_vector(value) -> bool:
    if is_null(value):
        return False
    if isinstance(value, (Environment, Formula)):
        return False
    if isinstance(value, Function):
        return False
    if isinstance(value, Vec):
        return value.mode in {"logical", "integer", "double", "complex", "character", "raw", "list"}
    return False


def has_only_names(value) -> bool:
    if not isinstance(value, Vec):
        return True
    if value.dim is not None or value.klass or value.levels is not None or value.tzone is not None:
        return False
    if value.rownames is not None or value.dimnames is not None:
        return False
    return True


def find_missing(value) -> int:
    """1-based index of the first missing element, or 0."""
    if is_null(value) or isinstance(value, (Environment, Formula, Function)):
        return 0
    if not isinstance(value, Vec):
        value = wrap(value)
    if value.mode == "list" and "data.frame" in value.klass:
        return find_missing_frame(value)
    if value.mode == "raw":
        return 0
    for i, item in enumerate(value.data):
        if value.mode == "list":
            if is_null(item):
                return i + 1
        elif is_na_scalar(item, value.mode):
            return i + 1
    return 0


def find_missing_frame(value: Vec) -> int:
    for j, column in enumerate(value.data):
        if isinstance(column, Vec) and column.mode != "list":
            hit = find_missing(column)
            if hit:
                return j * len(column.data) + hit
    return 0


def all_missing(value) -> bool:
    if is_null(value):
        return False
    if isinstance(value, (Environment, Formula, Function)):
        raise CheckError(f"Object of type '{guess_type(value)}' not supported")
    if not isinstance(value, Vec):
        value = wrap(value)
    if value.mode == "raw":
        return False
    if value.mode == "list" and "data.frame" in value.klass:
        for column in value.data:
            if isinstance(column, Vec) and column.mode != "list" and all_missing(column):
                return True
        return False
    if value.mode == "list":
        return all(is_null(item) for item in value.data)
    if not value.data and value.mode in {"logical", "integer", "double", "complex", "character"}:
        return True
    return all(is_na_scalar(item, value.mode) for item in value.data)


def any_missing(value) -> bool:
    if is_null(value):
        return False
    if isinstance(value, (Environment, Formula, Function)):
        raise CheckError(f"Object of type '{guess_type(value)}' not supported")
    return find_missing(value if isinstance(value, Vec) else wrap(value)) > 0


def any_nan(value) -> bool:
    if is_null(value) or not isinstance(value, Vec):
        value = wrap(value) if not isinstance(value, (Environment, Formula, Function, _Null)) else value
    if not isinstance(value, Vec):
        return False
    if value.mode == "list":
        return any(any_nan(item) for item in value.data if isinstance(item, Vec))
    if value.mode == "double":
        return any(isinstance(item, float) and math.isnan(item) for item in value.data)
    if value.mode == "complex":
        for item in value.data:
            if isinstance(item, complex) and (math.isnan(item.real) or math.isnan(item.imag)):
                return True
    return False


def any_infinite(value) -> bool:
    if not isinstance(value, Vec):
        value = wrap(value) if not isinstance(value, (Environment, Formula, Function, _Null)) else value
    if not isinstance(value, Vec):
        return False
    if value.mode == "list":
        return any(any_infinite(item) for item in value.data if isinstance(item, Vec))
    if value.mode == "double":
        return any(isinstance(item, float) and math.isinf(item) for item in value.data)
    if value.mode == "complex":
        return any(
            isinstance(item, complex) and (math.isinf(item.real) or math.isinf(item.imag))
            for item in value.data
        )
    return False


def nrows(value) -> int:
    if isinstance(value, Vec) and "data.frame" in value.klass:
        if value.nrows is not None:
            return value.nrows
        if value.rownames is not None:
            return len(value.rownames)
        if value.data:
            return len(value.data[0].data)
        return 0
    if isinstance(value, Vec) and value.dim:
        return value.dim[0]
    return xlength(value)


def ncols(value) -> int:
    if isinstance(value, Vec) and "data.frame" in value.klass:
        return len(value.data)
    if isinstance(value, Vec) and value.dim and len(value.dim) >= 2:
        return value.dim[1]
    return 1


def nchar_bytes(text: str) -> int:
    return len(text.encode("utf-8"))


def fmt_g(number: float) -> str:
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return format(float(number), ".6g")


def message(fmt: str, *args) -> str:
    text = fmt % args if args else fmt
    if len(text) > 254:
        text = text[:254]
    return text


def os_name() -> str:
    system = os.uname().sysname.lower()
    return {"windows": "windows", "darwin": "mac", "linux": "linux", "sunos": "solaris"}.get(system, system)


def caller_arg(depth: int = 2) -> str:
    """Best-effort deparse of the caller's first argument, for vname."""
    frame = sys._getframe(depth)
    try:
        info = inspect.getframeinfo(frame)
        line = info.code_context[0].strip() if info.code_context else ""
    except Exception:
        return "x"
    if "(" not in line:
        return "x"
    inner = line.split("(", 1)[1]
    depth_paren = 0
    buf = []
    for ch in inner:
        if ch == "(":
            depth_paren += 1
        elif ch == ")" and depth_paren == 0:
            break
        elif ch == "," and depth_paren == 0:
            break
        buf.append(ch)
    text = "".join(buf).strip()
    return text or "x"
