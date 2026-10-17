"""Ports of checkmate's C checks and the R wrappers that only add a pattern or a type list."""

from __future__ import annotations

import math
import re
import warnings

from .rtypes import (
    DEFAULT_TOL,
    INT_MAX,
    INT_MIN,
    NA,
    CheckError,
    Vec,
    all_missing,
    any_infinite,
    find_missing,
    fmt_g,
    guess_type,
    has_only_names,
    is_class_array,
    is_class_atomic,
    is_class_atomic_vector,
    is_class_complex,
    is_class_double,
    is_class_factor,
    is_class_frame,
    is_class_integer,
    is_class_list,
    is_class_logical,
    is_class_matrix,
    is_class_numeric,
    is_class_posixct,
    is_class_raw,
    is_class_string,
    is_na_scalar,
    is_null,
    is_vector,
    message,
    ncols,
    nchar_bytes,
    nrows,
    wrap,
    xlength,
)

OK = True


def _flag(value, name: str) -> bool:
    obj = wrap(value) if not isinstance(value, (Vec,)) and value is not None else value
    if value is None or is_null(value):
        raise CheckError(f"Argument '{name}' must be a flag, but is NULL")
    if not (isinstance(obj, Vec) and obj.mode == "logical" and len(obj.data) == 1):
        raise CheckError(f"Argument '{name}' must be a flag, but is {guess_type(obj)}")
    if obj.data[0] is NA:
        raise CheckError(f"Argument '{name}' may not be missing")
    return bool(obj.data[0])


def _number(value, name: str) -> float:
    obj = wrap(value)
    if not is_class_numeric(obj):
        raise CheckError(f"Argument '{name}' must be a number, but is {guess_type(obj)}")
    if xlength(obj) != 1:
        raise CheckError(f"Argument '{name}' must have length 1, but has length {fmt_g(float(xlength(obj)))}")
    item = obj.data[0]
    if is_na_scalar(item, obj.mode):
        raise CheckError(f"Argument '{name}' may not be missing")
    return float(item)


def _string(value, name: str) -> str:
    obj = wrap(value)
    if not is_class_string(obj) or xlength(obj) != 1:
        raise CheckError(f"Argument '{name}' must be a string, but is {guess_type(obj)}")
    if obj.data[0] is NA:
        raise CheckError(f"Argument '{name}' may not be missing")
    return obj.data[0]


def _length(value, name: str) -> int:
    obj = wrap(value)
    if xlength(obj) != 1:
        raise CheckError(f"Argument '{name}' must have length 1")
    item = obj.data[0]
    if obj.mode == "integer":
        if item is NA:
            raise CheckError(f"Argument '{name}' may not be missing")
        if item < 0:
            raise CheckError(f"Argument '{name}' must be >= 0")
        return int(item)
    if obj.mode == "double":
        if is_na_scalar(item, "double"):
            raise CheckError(f"Argument '{name}' may not be missing")
        if item < 0:
            raise CheckError(f"Argument '{name}' must be >= 0")
        if abs(item - round(item)) >= DEFAULT_TOL:
            raise CheckError(f"Argument '{name}' is not close to an integer")
        return int(item)
    raise CheckError(f"Argument '{name}' must be a length, but is {guess_type(obj)}")


def _count(value, name: str) -> int:
    obj = wrap(value)
    if xlength(obj) != 1:
        raise CheckError(f"Argument '{name}' must have length 1")
    if not _integerish_ok(obj, DEFAULT_TOL, False):
        raise CheckError(f"Argument '{name}' must be numeric and close to an integer")
    xi = _as_integer(obj)
    if xi is None:
        raise CheckError(f"Argument '{name}' may not be missing")
    if xi < 0:
        raise CheckError(f"Argument '{name}' must be >= 0")
    return xi


def _as_integer(obj: Vec):
    item = obj.data[0]
    if is_na_scalar(item, obj.mode):
        return None
    if obj.mode == "integer":
        return int(item)
    return int(float(item))


def _scalar_na(obj) -> bool:
    if not isinstance(obj, Vec) or xlength(obj) != 1:
        return False
    return is_na_scalar(obj.data[0], obj.mode)


def _dup_key(item, mode: str):
    if item is NA:
        return ("NA", mode)
    if mode == "double" and isinstance(item, float) and math.isnan(item):
        return ("NaN",)
    if mode == "complex" and isinstance(item, complex):
        return (_dup_key(item.real, "double"), _dup_key(item.imag, "double"))
    if mode == "list":
        if is_null(item):
            return ("NULL",)
        if isinstance(item, Vec):
            return (item.mode, tuple(_dup_key(part, item.mode) for part in item.data), item.klass)
        return ("obj", repr(item))
    return (mode, item)


def any_duplicated(obj: Vec) -> int:
    seen = {}
    for i, item in enumerate(obj.data):
        key = _dup_key(item, obj.mode)
        if key in seen:
            return i + 1
        seen[key] = i
    return 0


def _unconvertible_double(item, tol: float) -> str | None:
    if is_na_scalar(item, "double"):
        return None
    number = float(item)
    if number <= INT_MIN or number > INT_MAX:
        return "range"
    if abs(number - round(number)) > tol:
        return "tol"
    return None


def _integerish_error(obj: Vec, tol: float, logicals_ok: bool):
    """Return (pos, kind) or None. kind is type, range, tol, complex."""
    if isinstance(obj, Vec) and obj.mode == "integer":
        if "factor" in obj.klass:
            return (0, "type")
        return None
    if isinstance(obj, Vec) and obj.mode == "logical":
        if logicals_ok or all_missing(obj):
            return None
        return (0, "type")
    if isinstance(obj, Vec) and obj.mode == "double":
        if "Date" in obj.klass or "POSIXt" in obj.klass:
            return (0, "type")
        for i, item in enumerate(obj.data):
            kind = _unconvertible_double(item, tol)
            if kind:
                return (i + 1, kind)
        return None
    if isinstance(obj, Vec) and obj.mode == "complex":
        for i, item in enumerate(obj.data):
            if item is NA:
                continue
            if isinstance(item, complex):
                if not math.isnan(item.imag) and abs(item.imag) > tol:
                    return (i + 1, "complex")
                kind = _unconvertible_double(item.real, tol)
                if kind:
                    return (i + 1, kind)
        return None
    return (0, "type")


def _integerish_ok(obj, tol: float, logicals_ok: bool) -> bool:
    return _integerish_error(obj, tol, logicals_ok) is None


def is_integerish(x, tol=DEFAULT_TOL) -> bool:
    obj = wrap(x)
    tol = float(wrap(tol).data[0])
    return _integerish_ok(obj, tol, False)


def _typed_missing_passes(obj, typed_missing) -> bool:
    if _flag(typed_missing, "typed.missing"):
        return False
    return not (isinstance(obj, Vec) and obj.mode == "list") and all_missing(obj)


def _type_null(obj, pred, expected: str, null_ok):
    if is_null(obj):
        if _flag(null_ok, "null.ok"):
            return OK
        return message("Must be of type '%s', not 'NULL'", expected)
    if pred(obj) or _typed_missing_passes(obj, typed_missing=False) and False:
        return None
    return None


def _require_type(obj, pred, expected: str, null_ok, typed_missing=False, use_typed=False):
    if is_null(obj):
        if _flag(null_ok, "null.ok"):
            return OK
        return message("Must be of type '%s', not 'NULL'", expected)
    ok = pred(obj)
    if not ok and use_typed and _typed_missing_passes(obj, typed_missing):
        ok = True
    if not ok:
        suffix = " (or 'NULL')" if _flag(null_ok, "null_ok") else ""
        return message("Must be of type '%s'%s, not '%s'", expected, suffix, guess_type(obj))
    return None


def _bounds(obj: Vec, lower, upper) -> str | None:
    if lower is not None:
        tmp = _number(lower, "lower")
        if math.isfinite(tmp) or math.isinf(tmp) and tmp > 0:
            for i, item in enumerate(obj.data):
                if obj.mode == "double" and not is_na_scalar(item, "double") and float(item) < tmp:
                    return message("Element %i is not >= %s", i + 1, fmt_g(tmp))
                if obj.mode == "integer" and item is not NA and item < tmp:
                    return message("Element %i is not >= %s", i + 1, fmt_g(tmp))
    if upper is not None:
        tmp = _number(upper, "upper")
        if math.isfinite(tmp) or math.isinf(tmp) and tmp < 0:
            for i, item in enumerate(obj.data):
                if obj.mode == "double" and not is_na_scalar(item, "double") and float(item) > tmp:
                    return message("Element %i is not <= %s", i + 1, fmt_g(tmp))
                if obj.mode == "integer" and item is not NA and item > tmp:
                    return message("Element %i is not <= %s", i + 1, fmt_g(tmp))
    return None


def _vector_len(obj, len_, min_len, max_len) -> str | None:
    n = xlength(obj)
    if len_ is not None:
        want = _length(len_, "len")
        if n != want:
            return message("Must have length %s, but has length %s", fmt_g(float(want)), fmt_g(float(n)))
    if min_len is not None:
        want = _length(min_len, "min.len")
        if n < want:
            return message("Must have length >= %s, but has length %s", fmt_g(float(want)), fmt_g(float(n)))
    if max_len is not None:
        want = _length(max_len, "max.len")
        if n > want:
            return message("Must have length <= %s, but has length %s", fmt_g(float(want)), fmt_g(float(n)))
    return None


def _vector_missings(obj, any_missing, all_missing_ok) -> str | None:
    if not _flag(any_missing, "any.missing"):
        pos = find_missing(obj)
        if pos:
            return message("Contains missing values (element %i)", pos)
    if not _flag(all_missing_ok, "all.missing") and all_missing(obj):
        return message("Contains only missing values")
    return None


def _vector_unique(obj, unique) -> str | None:
    if _flag(unique, "unique"):
        pos = any_duplicated(obj)
        if pos:
            return message("Contains duplicated values, position %i", pos)
    return None


def _strict_name(text: str) -> bool:
    i = 0
    while i < len(text) and text[i] == ".":
        i += 1
    if i >= len(text) or not text[i].isalpha():
        return False
    for ch in text[i:]:
        if not (ch.isalnum() or ch in "._"):
            return False
    return True


def _check_names(names, kind: str, what: str) -> str | None:
    if kind == "unnamed":
        if names is None:
            return None
        return message("May not have %s", what)
    if kind not in {"named", "unique", "strict", "ids"}:
        raise CheckError(
            f"Unknown type '{kind}' to specify check for names. "
            "Supported are 'unnamed', 'named', 'unique' and 'strict'."
        )
    if names is None:
        return message("Must have %s", what)
    for i, name in enumerate(names):
        if name is NA:
            return message("Must have %s, but is NA at position %i", what, i + 1)
    for i, name in enumerate(names):
        if name is not NA and nchar_bytes(name) < 1:
            return message("Must have %s, but element %i is empty", what, i + 1)
    if kind in {"unique", "strict"}:
        seen = {}
        for i, name in enumerate(names):
            if name in seen:
                return message("Must have unique %s, but element %i is duplicated", what, i + 1)
            seen[name] = i
    if kind in {"strict", "ids"}:
        for i, name in enumerate(names):
            if name is NA or not _strict_name(str(name)):
                return message(
                    "Must have %s according to R's variable naming conventions, but element %i does not comply",
                    what,
                    i + 1,
                )
    return None


def _vector_names(obj: Vec, names) -> str | None:
    if names is not None and xlength(obj) > 0:
        return _check_names(obj.names, _string(names, "names"), "names")
    return None


def _sorted(obj: Vec) -> bool:
    if obj.mode == "integer":
        data = obj.data
        i = 0
        n = len(data)
        while i < n and data[i] is NA:
            i += 1
        for j in range(i + 1, n):
            if data[j] is not NA:
                if data[i] > data[j]:
                    return False
                i = j
        return True
    if obj.mode == "double":
        data = obj.data
        i = 0
        n = len(data)

        def _isna(item):
            return item is NA

        while i < n and _isna(data[i]):
            i += 1
        for j in range(i + 1, n):
            if not _isna(data[j]):
                if float(data[i]) > float(data[j]):
                    return False
                i = j
        return True
    if obj.mode == "character":
        data = obj.data
        i = 0
        n = len(data)
        while i < n and data[i] is NA:
            i += 1
        for j in range(i + 1, n):
            if data[j] is not NA:
                if data[i] > data[j]:
                    return False
                i = j
        return True
    raise CheckError("Checking for sorted vector only possible for integer and double")


def _vector_sorted(obj, sorted_) -> str | None:
    if _flag(sorted_, "sorted") and xlength(obj) > 1 and not _sorted(obj):
        return message("Must be sorted")
    return None


def _vector_finite(obj, finite) -> str | None:
    if _flag(finite, "finite") and any_infinite(obj):
        return message("Must be finite")
    return None


def _nchar(obj: Vec, n: int, cmp) -> int:
    for i, item in enumerate(obj.data):
        if item is NA:
            continue
        if not cmp(nchar_bytes(item), n):
            return i + 1
    return 0


def _string_nchar(obj, n_chars, min_chars, max_chars) -> str | None:
    if n_chars is not None:
        n = _count(n_chars, "n.chars")
        pos = _nchar(obj, n, lambda a, b: a == b)
        if pos:
            return message(
                "All elements must have exactly %i characters, but element %i has %i chararacters",
                n,
                pos,
                nchar_bytes(obj.data[pos - 1]),
            )
    if min_chars is not None:
        n = _count(min_chars, "min.chars")
        pos = _nchar(obj, n, lambda a, b: a >= b)
        if pos:
            return message(
                "All elements must have at least %i characters, but element %i has %i characters",
                n,
                pos,
                nchar_bytes(obj.data[pos - 1]),
            )
    if max_chars is not None:
        n = _count(max_chars, "max.chars")
        pos = _nchar(obj, n, lambda a, b: a <= b)
        if pos:
            return message(
                "All elements must have at most %i characters, but element %i has %i characters",
                n,
                pos,
                nchar_bytes(obj.data[pos - 1]),
            )
    return None


def _matrix_dims(obj, min_rows, max_rows, min_cols, max_cols, rows, cols) -> str | None:
    if min_rows is not None or max_rows is not None or rows is not None:
        got = nrows(obj)
        if min_rows is not None:
            want = _length(min_rows, "min.rows")
            if got < want:
                return message("Must have at least %i rows, but has %i rows", want, got)
        if max_rows is not None:
            want = _length(max_rows, "max.rows")
            if got > want:
                return message("Must have at most %i rows, but has %i rows", want, got)
        if rows is not None:
            want = _length(rows, "rows")
            if got != want:
                return message("Must have exactly %i rows, but has %i rows", want, got)
    if min_cols is not None or max_cols is not None or cols is not None:
        got = ncols(obj)
        if min_cols is not None:
            want = _length(min_cols, "min.cols")
            if got < want:
                return message("Must have at least %i cols, but has %i cols", want, got)
        if max_cols is not None:
            want = _length(max_cols, "max.cols")
            if got > want:
                return message("Must have at most %i cols, but has %i cols", want, got)
        if cols is not None:
            want = _count(cols, "cols")
            if got != want:
                return message("Must have exactly %i cols, but has %i cols", want, got)
    return None


def _storage(obj, mode) -> str | None:
    if mode is None or all_missing(obj):
        return None
    storage = _string(mode, "mode")
    checks = {
        "logical": (is_class_logical, "Must store logicals"),
        "integer": (is_class_integer, "Must store integers"),
        "double": (is_class_double, "Must store doubles"),
        "integerish": (lambda value: _integerish_ok(value, DEFAULT_TOL, False), "Must store integerish values"),
        "numeric": (is_class_numeric, "Must store numerics"),
        "complex": (is_class_complex, "Must store complexs"),
        "character": (is_class_string, "Must store characters"),
        "list": (is_class_list, "Must store a list"),
        "atomic": (lambda value: isinstance(value, Vec) and value.mode != "list", "Must be atomic"),
    }
    if storage not in checks:
        raise CheckError(
            "Invalid argument 'mode'. Must be one of 'logical', 'integer', 'integerish', "
            "'double', 'numeric', 'complex', 'character', 'list' or 'atomic'"
        )
    pred, text = checks[storage]
    if not pred(obj):
        return text
    return None


def _finish_vector(obj, any_missing, all_missing_ok, len_, min_len, max_len, unique, names,
                   lower=None, upper=None, finite=None, sorted_=None) -> str | bool:
    for part in (
        _vector_len(obj, len_, min_len, max_len),
        _vector_names(obj, names),
        _vector_missings(obj, any_missing, all_missing_ok),
    ):
        if part:
            return part
    if lower is not None or upper is not None:
        hit = _bounds(obj, lower, upper)
        if hit:
            return hit
    if finite is not None:
        hit = _vector_finite(obj, finite)
        if hit:
            return hit
    hit = _vector_unique(obj, unique)
    if hit:
        return hit
    if sorted_ is not None:
        hit = _vector_sorted(obj, sorted_)
        if hit:
            return hit
    return OK


def checkLogical(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None,
                 unique=False, names=None, typed_missing=False, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_logical, "logical", null_ok, typed_missing, True)
    if hit is not None:
        return hit
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names)


def checkInteger(x, lower=-math.inf, upper=math.inf, any_missing=True, all_missing=True, len=None,
                 min_len=None, max_len=None, unique=False, sorted=False, names=None,
                 typed_missing=False, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_integer, "integer", null_ok, typed_missing, True)
    if hit is not None:
        return hit
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names,
                          lower, upper, sorted_=sorted)


def checkIntegerish(x, tol=DEFAULT_TOL, lower=-math.inf, upper=math.inf, any_missing=True,
                    all_missing=True, len=None, min_len=None, max_len=None, unique=False,
                    sorted=False, names=None, typed_missing=False, null_ok=False):
    obj = wrap(x)
    dtol = _number(tol, "tol")
    if is_null(obj):
        if _flag(null_ok, "null.ok"):
            return OK
        return message("Must be of type 'integerish', not 'NULL'")
    err = _integerish_error(obj, dtol, False)
    if err is not None:
        pos, kind = err
        if kind == "type":
            if not _typed_missing_passes(obj, typed_missing):
                suffix = " (or 'NULL')" if _flag(null_ok, "null_ok") else ""
                return message("Must be of type 'integerish'%s, not '%s'", suffix, guess_type(obj))
        elif kind == "range":
            return message("Must be of type 'integerish', but element %s is not in integer range", fmt_g(float(pos)))
        elif kind == "tol":
            return message("Must be of type 'integerish', but element %s is not close to an integer", fmt_g(float(pos)))
        elif kind == "complex":
            return message("Must be of type 'integerish', but element %s has an imaginary part", fmt_g(float(pos)))
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names,
                          lower, upper, sorted_=sorted)


def checkDouble(x, lower=-math.inf, upper=math.inf, finite=False, any_missing=True, all_missing=True,
                len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None,
                typed_missing=False, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_double, "double", null_ok, typed_missing, True)
    if hit is not None:
        return hit
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names,
                          lower, upper, finite, sorted)


def checkNumeric(x, lower=-math.inf, upper=math.inf, finite=False, any_missing=True, all_missing=True,
                 len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None,
                 typed_missing=False, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_numeric, "numeric", null_ok, typed_missing, True)
    if hit is not None:
        return hit
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names,
                          lower, upper, finite, sorted)


def checkComplex(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None,
                 unique=False, names=None, typed_missing=False, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_complex, "complex", null_ok, typed_missing, True)
    if hit is not None:
        return hit
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names)


def checkCharacter(x, n_chars=None, min_chars=None, max_chars=None, pattern=None, fixed=None,
                   ignore_case=False, any_missing=True, all_missing=True, len=None, min_len=None,
                   max_len=None, unique=False, sorted=False, names=None, typed_missing=False,
                   null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_string, "character", null_ok, typed_missing, True)
    if hit is None:
        hit = _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names, sorted_=sorted)
        if hit is OK:
            hit = _string_nchar(obj, n_chars, min_chars, max_chars)
    pattern_hit = _character_pattern(obj, pattern, fixed, ignore_case)
    if hit is None:
        return pattern_hit
    if hit is not OK:
        return hit
    return pattern_hit


def _character_pattern(obj, pattern, fixed, ignore_case):
    if is_null(obj):
        return OK
    flags = re.IGNORECASE if _flag(ignore_case, "ignore.case") else 0
    if pattern is not None:
        from .qassert import qassert
        qassert(pattern, "S1")
        pat = _string(pattern, "pattern")
        texts = [item for item in obj.data if item is not NA] if isinstance(obj, Vec) else []
        if isinstance(obj, Vec) and obj.mode == "character":
            if not all(re.search(pat, item, flags) for item in texts):
                return message("Must comply to pattern '%s'", pat)
        else:
            shown = [str(item) for item in (obj.data if isinstance(obj, Vec) else []) if item is not NA]
            if shown and not all(re.search(pat, item, flags) for item in shown):
                return message("Must comply to pattern '%s'", pat)
    if fixed is not None:
        from .qassert import qassert
        qassert(fixed, "S1")
        needle = _string(fixed, "fixed")
        if flags:
            needle = needle.lower()
        texts = []
        if isinstance(obj, Vec):
            texts = [item for item in obj.data if item is not NA and isinstance(item, str)]
        if not all((needle in (item.lower() if flags else item)) for item in texts):
            return message("Must contain substring '%s'", _string(fixed, "fixed"))
    return OK


def checkFactor(x, levels=None, ordered=NA, empty_levels_ok=True, any_missing=True, all_missing=True,
                len=None, min_len=None, max_len=None, n_levels=None, min_levels=None, max_levels=None,
                unique=False, names=None, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_factor, "factor", null_ok, use_typed=False)
    if hit is None:
        hit = _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names)
    extra = _factor_levels(obj, levels, ordered, empty_levels_ok, n_levels, min_levels, max_levels)
    if hit not in (None, OK):
        return hit
    return extra


def _factor_levels(obj, levels, ordered, empty_levels_ok, n_levels, min_levels, max_levels):
    if is_null(obj):
        return OK
    from .qassert import qassert
    if levels is not None:
        qassert(levels, "S")
        wanted = list(wrap(levels).data)
        have = list(obj.levels or [])
        if set(have) != set(wanted) or len(have) != len(set(wanted)):
            if sorted(have) != sorted(wanted):
                return message("Must have levels: %s", "".join(str(item) for item in [",".join(wanted)]))
    if not (ordered is NA or (isinstance(ordered, Vec) and len(ordered.data) == 1 and ordered.data[0] is NA)
            and not isinstance(ordered, bool)):
        qassert(ordered, "b1")
    ordered_obj = wrap(ordered) if not isinstance(ordered, bool) and ordered is not NA else None
    if ordered is NA or (isinstance(ordered, Vec) and ordered.data and ordered.data[0] is NA):
        pass
    else:
        qassert(ordered, "b1")
        flag = ordered if isinstance(ordered, bool) else bool(wrap(ordered).data[0])
        if wrap(ordered).data[0] is NA:
            flag = None
        if flag is True and not (isinstance(obj, Vec) and obj.ordered):
            return "Must be an ordered factor, but is unordered"
        if flag is False and isinstance(obj, Vec) and obj.ordered:
            return "Must be an unordered factor, but is ordered"
    qassert(empty_levels_ok, "B1")
    if not _flag(empty_levels_ok, "empty.levels.ok") and isinstance(obj, Vec):
        used = set()
        for code in obj.data:
            if code is not NA:
                used.add(obj.levels[code - 1])
        empty = [level for level in obj.levels if level not in used]
        if empty:
            return message("Has has empty levels '%s'", "','".join(empty))
    have_n = len(obj.levels or []) if isinstance(obj, Vec) else 0
    if n_levels is not None:
        qassert(n_levels, "X1")
        if have_n != _as_integer(wrap(n_levels)):
            return message("Must have exactly %i levels", _as_integer(wrap(n_levels)))
    if min_levels is not None:
        qassert(min_levels, "X1")
        if have_n < _as_integer(wrap(min_levels)):
            return message("Must have at least %i levels", _as_integer(wrap(min_levels)))
    if max_levels is not None:
        qassert(max_levels, "X1")
        if have_n > _as_integer(wrap(max_levels)):
            return message("Must have at most %i levels", _as_integer(wrap(max_levels)))
    return OK


def checkRaw(x, len=None, min_len=None, max_len=None, names=None, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_raw, "raw", null_ok, use_typed=False)
    if hit is not None:
        return hit
    for part in (_vector_len(obj, len, min_len, max_len), _vector_names(obj, names)):
        if part:
            return part
    return OK


def checkAtomic(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None,
                unique=False, names=None):
    obj = wrap(x)
    if not is_class_atomic(obj):
        return message("Must be of type 'atomic', not '%s'", guess_type(obj))
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names)


def checkAtomicVector(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None,
                      unique=False, names=None):
    obj = wrap(x)
    if not is_class_atomic_vector(obj):
        return message("Must be of type 'atomic vector', not '%s'", guess_type(obj))
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names)


def checkVector(x, strict=False, any_missing=True, all_missing=True, len=None, min_len=None,
                max_len=None, unique=False, names=None, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_vector, "vector", null_ok, use_typed=False)
    if hit is not None:
        return hit
    if _flag(strict, "strict") and not has_only_names(obj):
        return message("Must be of type 'vector', not '%s'", guess_type(obj))
    return _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names)


def checkList(x, types=None, any_missing=True, all_missing=True, len=None, min_len=None,
              max_len=None, unique=False, names=None, null_ok=False):
    obj = wrap(x)
    if types is None:
        types = character([])
    hit = _require_type(obj, is_class_list, "list", null_ok, use_typed=False)
    if hit is None:
        hit = _finish_vector(obj, any_missing, all_missing, len, min_len, max_len, unique, names)
    extra = _list_types(obj, types)
    if hit not in (None, OK):
        return hit
    return extra


def _list_types(obj, types):
    if is_null(obj) or xlength(obj) == 0 or types is None or xlength(wrap(types)) == 0:
        return OK
    from .qassert import qassert
    qassert(types, "S")
    wanted = list(wrap(types).data)
    pending = list(range(len(obj.data)))
    for kind in wanted:
        pending = [i for i in pending if not _is_list_type(obj.data[i], kind)]
        if not pending:
            return OK
    element = obj.data[pending[0]]
    shown = ",".join(rclass_text(element))
    return message(
        "May only contain the following types: {%s}, but element %i has type '%s'",
        ",".join(wanted),
        pending[0] + 1,
        shown,
    )


def rclass_text(value) -> list[str]:
    from .rtypes import rclass
    return list(rclass(value))


def _is_list_type(element, kind: str) -> bool:
    obj = element if isinstance(element, Vec) else wrap(element)
    table = {
        "logical": is_class_logical,
        "integer": is_class_integer,
        "integerish": lambda value: _integerish_ok(value, DEFAULT_TOL, False),
        "double": is_class_double,
        "numeric": is_class_numeric,
        "complex": is_class_complex,
        "character": is_class_string,
        "factor": is_class_factor,
        "atomic": lambda value: not is_null(value) and is_class_atomic(value),
        "vector": is_vector,
        "atomicvector": is_class_atomic_vector,
        "array": is_class_array,
        "matrix": is_class_matrix,
        "list": is_class_list,
        "function": lambda value: getattr(value, "mode", None) == "function",
        "environment": lambda value: getattr(value, "mode", None) == "environment",
        "null": is_null,
    }
    if kind in table:
        return bool(table[kind](obj))
    from .rtypes import inherits
    return inherits(obj, kind)


def checkMatrix(x, mode=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None,
                min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None,
                null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_matrix, "matrix", null_ok, use_typed=False)
    if hit is not None:
        return hit
    stored = _storage(obj, mode)
    if stored:
        return stored
    dims = _matrix_dims(obj, min_rows, max_rows, min_cols, max_cols, nrows, ncols)
    if dims:
        return dims
    if row_names is not None and xlength(obj) > 0:
        row = None if not obj.dimnames else obj.dimnames[0]
        hit = _check_names(row, _string(row_names, "row.names"), "rownames")
        if hit:
            return hit
    if col_names is not None and xlength(obj) > 0:
        col = None if not obj.dimnames or len(obj.dimnames) < 2 else obj.dimnames[1]
        hit = _check_names(col, _string(col_names, "col.names"), "colnames")
        if hit:
            return hit
    if not _flag(any_missing, "any.missing"):
        pos = find_missing(obj)
        if pos:
            got = nrows(obj)
            return message(
                "Contains missing values (row %i, col %i)",
                (pos - 1) % got + 1,
                (pos - 1) // got + 1,
            )
    if not _flag(all_missing, "all.missing") and all_missing(obj):
        return message("Contains only missing values")
    return OK


def checkArray(x, mode=None, any_missing=True, d=None, min_d=None, max_d=None, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_array, "array", null_ok, use_typed=False)
    if hit is not None:
        return hit
    stored = _storage(obj, mode)
    if stored:
        return stored
    if not _flag(any_missing, "any.missing") and find_missing(obj):
        return message("Contains missing values")
    ndim = 0 if obj.dim is None else len(obj.dim)
    if d is not None:
        di = _count(d, "d")
        if ndim != di:
            return message("Must be a %i-d array, but has dimension %i", di, ndim)
    if min_d is not None:
        di = _count(min_d, "min.d")
        if ndim < di:
            return message("Must have >=%i dimensions, but has dimension %i", di, ndim)
    if max_d is not None:
        di = _count(max_d, "max.d")
        if ndim > di:
            return message("Must have <=%i dimensions, but has dimension %i", di, ndim)
    return OK


def checkDataFrame(x, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None,
                   min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None,
                   col_names=None, null_ok=False):
    obj = wrap(x)
    if types is None:
        types = character([])
    hit = _require_type(obj, is_class_frame, "data.frame", null_ok, use_typed=False)
    if hit is not None:
        return hit
    dims = _matrix_dims(obj, min_rows, max_rows, min_cols, max_cols, nrows, ncols)
    if dims:
        return dims
    if row_names is not None:
        names = obj.rownames
        if names is not None and names and isinstance(names[0], int):
            names = [str(item) for item in names]
        hit = _check_names(names, _string(row_names, "row.names"), "rownames")
        if hit:
            return hit
    if col_names is not None:
        hit = _check_names(obj.names, _string(col_names, "col.names"), "colnames")
        if hit:
            return hit
    if not _flag(any_missing, "any.missing"):
        pos = find_missing(obj)
        if pos:
            got = nrows(obj)
            col = (pos - 1) // got
            row = (pos - 1) % got
            label = obj.names[col] if obj.names else ""
            return message("Contains missing values (column '%s', row %i)", label, row + 1)
    if not _flag(all_missing, "all.missing") and all_missing(obj):
        return message("Contains only missing values")
    return _list_types(obj, types)


def checkNamed(x, type="named"):
    warnings.warn(
        "'checkNamed' is deprecated.\nUse 'checkNames' instead.\n"
        'See help("Deprecated") and help("checkmate-deprecated").',
        stacklevel=2,
    )
    obj = wrap(x)
    if type is not None and xlength(obj) > 0:
        hit = _check_names(obj.names, _string(type, "type"), "Object")
        if hit:
            return hit
    return OK


def checkNames(x, type="named", subset_of=None, must_include=None, permutation_of=None,
               identical_to=None, disjunct_from=None, what="names"):
    obj = wrap(x)
    if not (is_null(obj) or is_class_string(obj)):
        return message("Must be a character vector")
    names = None if is_null(obj) else obj.data
    hit = _check_names(names, _string(type, "type"), _string(what, "what"))
    if hit:
        return hit
    from .sets import names_compare
    return names_compare(obj, subset_of, must_include, permutation_of, identical_to, disjunct_from, _string(what, "what"))


def checkFlag(x, na_ok=False, null_ok=False):
    obj = wrap(x)
    if _scalar_na(obj):
        if _flag(na_ok, "na.ok"):
            return OK
        return message("May not be NA")
    hit = _require_type(obj, is_class_logical, "logical flag", null_ok, use_typed=False)
    if hit is not None:
        return hit
    if xlength(obj) != 1:
        return message("Must have length 1")
    return OK


def checkCount(x, na_ok=False, positive=False, tol=DEFAULT_TOL, null_ok=False):
    obj = wrap(x)
    if _scalar_na(obj):
        if _flag(na_ok, "na.ok"):
            return OK
        return message("May not be NA")
    dtol = _number(tol, "tol")
    hit = _require_type(obj, lambda value: _integerish_ok(value, dtol, False), "count", null_ok, use_typed=False)
    if hit is not None:
        return hit
    if xlength(obj) != 1:
        return message("Must have length 1")
    pos = int(_flag(positive, "positive"))
    if _as_integer(obj) < pos:
        return message("Must be >= %i", pos)
    return OK


def checkInt(x, na_ok=False, lower=-math.inf, upper=math.inf, tol=DEFAULT_TOL, null_ok=False):
    obj = wrap(x)
    dtol = _number(tol, "tol")
    if _scalar_na(obj):
        if _flag(na_ok, "na.ok"):
            return OK
        return message("May not be NA")
    hit = _require_type(
        obj, lambda value: _integerish_ok(value, dtol, False), "single integerish value", null_ok, use_typed=False
    )
    if hit is not None:
        return hit
    if xlength(obj) != 1:
        return message("Must have length 1")
    bound = _bounds(obj, lower, upper)
    return bound or OK


def checkNumber(x, na_ok=False, lower=-math.inf, upper=math.inf, finite=False, null_ok=False):
    obj = wrap(x)
    if _scalar_na(obj):
        if _flag(na_ok, "na.ok"):
            return OK
        return message("May not be NA")
    hit = _require_type(obj, is_class_numeric, "number", null_ok, use_typed=False)
    if hit is not None:
        return hit
    if xlength(obj) != 1:
        return message("Must have length 1")
    finite_hit = _vector_finite(obj, finite)
    if finite_hit:
        return finite_hit
    bound = _bounds(obj, lower, upper)
    return bound or OK


def checkString(x, na_ok=False, n_chars=None, min_chars=None, max_chars=None, pattern=None,
                fixed=None, ignore_case=False, null_ok=False):
    obj = wrap(x)
    if _scalar_na(obj):
        if _flag(na_ok, "na.ok"):
            return OK
        return message("May not be NA")
    hit = _require_type(obj, is_class_string, "string", null_ok, use_typed=False)
    if hit is None and xlength(obj) != 1:
        hit = message("Must have length 1")
    if hit is None:
        hit = _string_nchar(obj, n_chars, min_chars, max_chars)
    pattern_hit = _character_pattern(obj, pattern, fixed, ignore_case)
    if hit not in (None, OK):
        return hit
    return pattern_hit


def checkScalar(x, na_ok=False, null_ok=False):
    obj = wrap(x)
    if _scalar_na(obj):
        if _flag(na_ok, "na.ok"):
            return OK
        return message("May not be NA")
    atomic = isinstance(obj, Vec) and obj.mode in {"logical", "integer", "double", "complex", "character", "raw"}
    hit = _require_type(obj, lambda value: atomic, "atomic scalar", null_ok, use_typed=False)
    if hit is not None:
        return hit
    if xlength(obj) != 1:
        return message("Must have length 1")
    return OK


def checkPOSIXct(x, lower=None, upper=None, any_missing=True, all_missing=True, len=None,
                 min_len=None, max_len=None, unique=False, sorted=False, null_ok=False):
    obj = wrap(x)
    hit = _require_type(obj, is_class_posixct, "POSIXct", null_ok, use_typed=False)
    if hit is not None:
        return hit
    for part in (
        _vector_len(obj, len, min_len, max_len),
        _vector_missings(obj, any_missing, all_missing),
        _vector_unique(obj, unique),
    ):
        if part:
            return part
    bound = _posix_bounds(obj, lower, upper)
    if bound:
        return bound
    if sorted is not None:
        hit = _vector_sorted(obj, sorted)
        if hit:
            return hit
    return OK


def _posix_bounds(obj: Vec, lower, upper) -> str | None:
    if lower is None and upper is None:
        return None
    for label, bound in (("lower", lower), ("upper", upper)):
        if bound is None:
            continue
        other = wrap(bound)
        if not is_class_posixct(other) or xlength(other) != 1:
            raise CheckError(f"Argument '{label}' must be provided as single POSIXct time")
        if (obj.tzone is None) != (other.tzone is None) or (
            obj.tzone is not None and other.tzone is not None and obj.tzone != other.tzone
        ):
            return message("Timezones of 'x' and '%s' must match", label)
        limit = float(other.data[0])
        for i, item in enumerate(obj.data):
            if item is NA or (isinstance(item, float) and math.isnan(item)):
                continue
            if label == "lower" and float(item) < limit:
                return message("Element %i is not >= %s", i + 1, _format_posix(other))
            if label == "upper" and float(item) > limit:
                return message("Element %i is not <= %s", i + 1, _format_posix(other))
    return None


def _format_posix(obj: Vec) -> str:
    import datetime
    stamp = float(obj.data[0])
    tz = datetime.timezone.utc if obj.tzone in {None, "UTC", "GMT"} else datetime.timezone.utc
    moment = datetime.datetime.fromtimestamp(stamp, tz=tz)
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def character(values, names=None):
    from .rtypes import character as _character
    return _character(values, names)
