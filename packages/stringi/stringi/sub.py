"""Code-point substring extract and replace, matching stringi 1.8.9.

``from_`` is R's ``from``. Python reserves that word. Indexes are 1-based
code points. A negative index counts from the end. Missing strings and
missing indexes are ``stringi._na.NA``; ``None`` in a vector is the same
missing value. A leading U+FEFF is dropped, as stringi drops a UTF-8 BOM.
"""

from __future__ import annotations

import math
import warnings

from stringi._na import NA

_MISSING = object()
_INT_MIN = -2147483647
_INT_MAX = 2147483647


class IndexMatrix:
    """Two-column index matrix stored by rows.

    Each row is one ``(from, to)`` pair, or ``(from, length)`` when the
    second column name is ``length``. A one-column matrix is a single
    index vector. More than two columns is an error.
    """

    def __init__(self, rows, colnames=None):
        parsed = []
        ncol = None
        for row in rows:
            items = list(row)
            if ncol is None:
                ncol = len(items)
            elif len(items) != ncol:
                raise ValueError("argument `from` should be a matrix with 2 columns")
            parsed.append(items)
        self.rows = parsed
        self.ncol = 0 if ncol is None else ncol
        self.colnames = None if colnames is None else tuple(colnames)


def stri_sub(
    str,
    from_=1,
    to=_MISSING,
    length=_MISSING,
    use_matrix=True,
    ignore_negative_length=False,
):
    """Extract code-point substrings.

    ``from_`` is R's ``from``. ``to`` is the inclusive end. ``length``
    replaces ``to`` when it is passed. A negative ``length`` is ``NA``
    unless ``ignore_negative_length`` drops that element.
    """

    use = _wrapper_use_matrix(use_matrix)
    ignore = _logical_1(ignore_negative_length, "ignore_negative_length")
    strings = _as_strings(str, "str")
    from_obj, to_obj, length_obj = _wrapper_indexes(
        from_, to, length, use, "the current context"
    )
    return _extract(strings, from_obj, to_obj, length_obj, use, ignore)


def stri_sub_assign(
    str,
    from_=1,
    to=_MISSING,
    length=_MISSING,
    omit_na=False,
    use_matrix=True,
    value=_MISSING,
):
    """Replace code-point substrings. This is R's ``stri_sub<-``."""

    if value is _MISSING:
        raise ValueError('argument "value" is missing, with no default')
    use = _wrapper_use_matrix(use_matrix)
    omit = _logical_1(omit_na, "omit_na")
    strings = _as_strings(str, "str")
    values = _as_strings(value, "value")
    from_obj, to_obj, length_obj = _wrapper_indexes(
        from_, to, length, use, "this context"
    )
    return _replace(strings, from_obj, to_obj, length_obj, values, omit, use)


def stri_sub_replace(*args, replacement=_MISSING, value=_MISSING, **kwargs):
    """Return ``stri_sub<-`` applied to ``replacement`` or ``value``.

    When both are passed, ``value`` is the one that is written.
    """

    if value is _MISSING:
        if replacement is _MISSING:
            raise ValueError('argument "replacement" is missing, with no default')
        value = replacement
    return stri_sub_assign(*args, value=value, **kwargs)


def stri_sub_all(
    str,
    from_=_MISSING,
    to=_MISSING,
    length=_MISSING,
    use_matrix=True,
    ignore_negative_length=True,
):
    """Extract several substrings from each string.

    A flat index vector is one set of indexes, shared by recycling.
    A list of vectors gives each string its own indexes. ``from_`` is
    R's ``from``. A negative ``length`` is dropped by default.
    """

    strings = _as_strings(str, "str")
    from_specs = _spec_list(from_, [1])
    if length is _MISSING:
        to_specs = _spec_list(-1 if to is _MISSING else to, [-1])
        width = [len(strings), len(from_specs), len(to_specs)]
        length_specs = None
    else:
        if to is not _MISSING:
            warnings.warn(
                "argument `to` is ignored in this context",
                UserWarning,
                stacklevel=2,
            )
        length_specs = _spec_list(length, [])
        to_specs = None
        width = [len(strings), len(from_specs), len(length_specs)]
    count = _recycle(width)
    if count == 0:
        return []
    use = _logical_1(use_matrix, "use_matrix")
    ignore = _logical_1(ignore_negative_length, "ignore_negative_length")
    out = []
    for i in range(count):
        one = [strings[i % len(strings)]]
        fr = from_specs[i % len(from_specs)]
        if length_specs is None:
            piece = _extract(one, fr, to_specs[i % len(to_specs)], None, use, ignore)
        else:
            piece = _extract(one, fr, None, length_specs[i % len(length_specs)], use, ignore)
        out.append(piece)
    return out


def stri_sub_all_assign(
    str,
    from_=_MISSING,
    to=_MISSING,
    length=_MISSING,
    omit_na=False,
    use_matrix=True,
    value=_MISSING,
):
    """Replace several substrings in each string. This is R's ``stri_sub_all<-``."""

    if value is _MISSING:
        raise ValueError('argument "value" is missing, with no default')
    omit = _logical_1(omit_na, "omit_na")
    use = _logical_1(use_matrix, "use_matrix")
    strings = _as_strings(str, "str")
    from_specs = _spec_list(from_, [1])
    values = _value_groups(value)
    if length is _MISSING:
        to_specs = _spec_list(-1 if to is _MISSING else to, [-1])
        length_specs = None
        width = [len(strings), len(from_specs), len(values), len(to_specs)]
    else:
        if to is not _MISSING:
            warnings.warn(
                "argument `to` is ignored in this context",
                UserWarning,
                stacklevel=2,
            )
        to_specs = None
        length_specs = _spec_list(length, [])
        width = [len(strings), len(from_specs), len(values), len(length_specs)]
    count = _recycle(width)
    if count == 0:
        return []
    out = []
    for i in range(count):
        text = strings[i % len(strings)]
        if text is NA:
            out.append(NA)
            continue
        fr = from_specs[i % len(from_specs)]
        repl = values[i % len(values)]
        if length_specs is None:
            out.append(
                _replace_many(
                    text, fr, to_specs[i % len(to_specs)], None, repl, omit, use
                )
            )
        else:
            out.append(
                _replace_many(
                    text,
                    fr,
                    None,
                    length_specs[i % len(length_specs)],
                    repl,
                    omit,
                    use,
                )
            )
    return out


def stri_sub_replace_all(*args, replacement=_MISSING, value=_MISSING, **kwargs):
    """Return ``stri_sub_all<-`` applied to ``replacement`` or ``value``."""

    if value is _MISSING:
        if replacement is _MISSING:
            raise ValueError('argument "replacement" is missing, with no default')
        value = replacement
    return stri_sub_all_assign(*args, value=value, **kwargs)


def _wrapper_indexes(from_, to, length, use, context):
    from_obj = _promote(from_)
    is_matrix = isinstance(from_obj, IndexMatrix)
    if length is _MISSING:
        if use and is_matrix and to is not _MISSING:
            warnings.warn(
                f"argument `to` is ignored in {context}",
                UserWarning,
                stacklevel=3,
            )
            return from_obj, None, None
        if to is _MISSING:
            to = -1
        return from_obj, to, None
    if to is not _MISSING:
        warnings.warn(
            f"argument `to` is ignored in {context}",
            UserWarning,
            stacklevel=3,
        )
    if use and is_matrix:
        warnings.warn(
            f"argument `length` is ignored in {context}",
            UserWarning,
            stacklevel=3,
        )
        return from_obj, None, None
    return from_obj, None, length


def _extract(strings, from_obj, to_obj, length_obj, use, ignore):
    froms, others, length_mode = _resolve(from_obj, to_obj, length_obj, use)
    count = _recycle([len(strings), len(froms), len(others)])
    if count == 0:
        return []
    out = []
    negatives = 0
    for i in range(count):
        piece, dropped = _extract_one(
            strings[i % len(strings)],
            froms[i % len(froms)],
            others[i % len(others)],
            length_mode,
        )
        if dropped:
            negatives += 1
        out.append(piece)
    if ignore and negatives and length_mode:
        kept = []
        for i, piece in enumerate(out):
            text = strings[i % len(strings)]
            cur_from = froms[i % len(froms)]
            cur_len = others[i % len(others)]
            if text is not NA and cur_from is not None and cur_len is not None and cur_len < 0:
                continue
            kept.append(piece)
        return kept
    return out


def _extract_one(text, cur_from, cur_to, length_mode):
    if text is NA or cur_from is None or cur_to is None:
        return NA, False
    if length_mode:
        if cur_to == 0:
            return "", False
        if cur_to < 0:
            return NA, True
        cur_to = cur_from + cur_to - 1
        if cur_from < 0 and cur_to >= 0:
            cur_to = -1
    start, end = _bounds(text, cur_from, cur_to)
    if end > start:
        return text[start:end], False
    return "", False


def _replace(strings, from_obj, to_obj, length_obj, values, omit, use):
    froms, others, length_mode = _resolve(from_obj, to_obj, length_obj, use)
    count = _recycle([len(strings), len(values), len(froms), len(others)])
    if count == 0:
        return []
    out = []
    for i in range(count):
        out.append(
            _replace_one(
                strings[i % len(strings)],
                froms[i % len(froms)],
                others[i % len(others)],
                length_mode,
                values[i % len(values)],
                omit,
            )
        )
    return out


def _replace_one(text, cur_from, cur_to, length_mode, repl, omit):
    if text is NA:
        return NA
    if cur_from is None or cur_to is None or repl is NA:
        return text if omit else NA
    if length_mode and cur_to < 0:
        return text
    if length_mode:
        if cur_to <= 0:
            cur_to = 0
        else:
            cur_to = cur_from + cur_to - 1
            if cur_from < 0 and cur_to >= 0:
                cur_to = -1
    start, end = _bounds(text, cur_from, cur_to)
    if end < start:
        end = start
    written = "" if repl is NA else repl
    return text[:start] + written + text[end:]


def _replace_many(text, from_obj, to_obj, length_obj, values, omit, use):
    froms, others, length_mode = _resolve(from_obj, to_obj, length_obj, use)
    count = _recycle([len(froms), len(others)])
    if count <= 0:
        return text
    if len(values) <= 0:
        warnings.warn("replacement has length zero", UserWarning, stacklevel=4)
        return NA
    if not omit:
        for i in range(count):
            if froms[i % len(froms)] is None or others[i % len(others)] is None:
                return NA
        for i in range(count):
            if values[i % len(values)] is NA:
                return NA
    n = len(text)
    parts = []
    last = 0
    replaced = 0
    for i in range(count):
        cur_from = froms[i % len(froms)]
        cur_to = others[i % len(others)]
        repl = values[i % len(values)]
        if (
            cur_from is None
            or cur_to is None
            or repl is NA
            or (length_mode and cur_to < 0)
        ):
            continue
        replaced += 1
        if cur_from < 0:
            cur_from = n + cur_from + 1
        if cur_from <= 0:
            cur_from = 1
        cur_from -= 1
        if cur_from >= n:
            cur_from = n
        if length_mode:
            if cur_to < 0:
                cur_to = 0
            cur_to = cur_from + cur_to
        else:
            if cur_to < 0:
                cur_to = n + cur_to + 1
            if cur_to < cur_from:
                cur_to = cur_from
        if cur_to >= n:
            cur_to = n
        if last > cur_from:
            raise ValueError("index ranges must be sorted and mutually disjoint")
        if cur_from > last:
            parts.append(text[last:cur_from])
        if repl:
            parts.append(repl)
        last = cur_to
    if last < n:
        parts.append(text[last:])
    if replaced and count % len(values) != 0:
        warnings.warn(
            "vector length not consistent with other arguments",
            UserWarning,
            stacklevel=4,
        )
    return "".join(parts)


def _resolve(from_obj, to_obj, length_obj, use):
    matrix = from_obj if isinstance(from_obj, IndexMatrix) else _promote(from_obj)
    if not isinstance(matrix, IndexMatrix):
        matrix = None
    if use and matrix is not None and matrix.ncol > 2:
        raise ValueError("argument `from` should be a matrix with 2 columns")
    if use and matrix is not None and matrix.ncol == 2:
        left = _as_ints([row[0] for row in matrix.rows], "from")
        right = [row[1] for row in matrix.rows]
        if matrix.colnames is not None and matrix.colnames[1] == "length":
            return left, _as_ints(right, "length"), True
        return left, _as_ints(right, "to"), False
    if matrix is not None:
        from_obj = _flatten(matrix)
    froms = _as_ints(from_obj, "from")
    if length_obj is not None:
        return froms, _as_ints(length_obj, "length"), True
    return froms, _as_ints(to_obj, "to"), False


def _bounds(text, cur_from, cur_to):
    n = len(text)
    if cur_from >= 0:
        start = cur_from - 1
        if start < 0:
            start = 0
        elif start > n:
            start = n
    else:
        start = n + cur_from
        if start < 0:
            start = 0
    if cur_to >= 0:
        end = 0 if cur_to <= 0 else cur_to
        if end > n:
            end = n
    else:
        back = -cur_to - 1
        end = n if back <= 0 else n - back
        if end < 0:
            end = 0
    return start, end


def _promote(obj):
    if isinstance(obj, IndexMatrix):
        return obj
    if isinstance(obj, dict):
        keys = list(obj)
        if len(keys) != 2:
            return obj
        columns = []
        for key in keys:
            value = obj[key]
            if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
                return obj
            columns.append(list(value))
        nrow = max((len(col) for col in columns), default=0)
        if any(len(col) != nrow for col in columns):
            raise ValueError("argument `from` should be a matrix with 2 columns")
        rows = [[columns[0][i], columns[1][i]] for i in range(nrow)]
        return IndexMatrix(rows, colnames=tuple(keys))
    if (
        isinstance(obj, (list, tuple))
        and obj
        and all(isinstance(row, (list, tuple)) and not isinstance(row, (str, bytes)) for row in obj)
        and all(_is_flat(row) for row in obj)
    ):
        return IndexMatrix(obj)
    return obj


def _spec_list(obj, default):
    if obj is _MISSING:
        return [list(default)]
    if isinstance(obj, IndexMatrix):
        return [obj]
    if isinstance(obj, dict):
        return [_promote(obj)]
    if isinstance(obj, (list, tuple)):
        if len(obj) == 0 or _is_flat(obj):
            return [list(obj)]
        specs = []
        for item in obj:
            if isinstance(item, IndexMatrix):
                specs.append(item)
            elif isinstance(item, dict):
                specs.append(_promote(item))
            elif item is None:
                specs.append([])
            elif isinstance(item, (list, tuple)):
                specs.append(_promote(item) if not _is_flat(item) else list(item))
            else:
                specs.append([item])
        return specs
    return [[obj]]


def _value_groups(value):
    if value is None:
        return [[]]
    if value is NA or isinstance(value, (str, bool, int, float)):
        return [_as_strings(value, "value")]
    if isinstance(value, (list, tuple)):
        if len(value) == 0 or _is_string_row(value):
            return [_as_strings(list(value), "value")]
        return [_as_strings(item, "value") for item in value]
    return [_as_strings(value, "value")]


def _is_flat(obj):
    return all(_is_scalar(item) for item in obj)


def _is_scalar(item):
    return item is None or item is NA or isinstance(item, (bool, int, float, str))


def _is_string_row(obj):
    return all(
        item is None or item is NA or isinstance(item, (bool, int, float, str))
        for item in obj
    )


def _flatten(matrix):
    out = []
    for col in range(matrix.ncol):
        for row in matrix.rows:
            out.append(row[col])
    return out


def _recycle(lengths):
    if any(n <= 0 for n in lengths):
        return 0
    longest = max(lengths)
    if any(longest % n != 0 for n in lengths):
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            UserWarning,
            stacklevel=4,
        )
    return longest


def _wrapper_use_matrix(value):
    if isinstance(value, bool):
        return bool(value)
    if (
        isinstance(value, (list, tuple))
        and len(value) == 1
        and isinstance(value[0], bool)
    ):
        return bool(value[0])
    return False


def _logical_1(value, name):
    items = _as_logicals(value)
    if len(items) == 0:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if len(items) > 1:
        warnings.warn(
            f"argument `{name}` should be a single logical value; only the first element is used",
            UserWarning,
            stacklevel=3,
        )
    if items[0] is None:
        raise ValueError(f"missing values in argument `{name}` is not supported")
    return items[0]


def _as_logicals(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
        return [_one_logical(item) for item in value]
    return [_one_logical(value)]


def _one_logical(value):
    if value is None or value is NA:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == -2147483648:
            return None
        return value != 0
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value != 0.0
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("true", "t"):
            return True
        if token in ("false", "f"):
            return False
        return None
    raise ValueError("argument should be a logical vector (or an object coercible to)")


class _IntState:
    def __init__(self):
        self.range_na = False
        self.parse_na = False


def _as_ints(obj, name):
    if obj is None:
        return []
    items = obj if isinstance(obj, (list, tuple)) else [obj]
    state = _IntState()
    out = [_one_int(item, state, name) for item in items]
    if state.range_na:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            UserWarning,
            stacklevel=4,
        )
    elif state.parse_na:
        warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=4)
    return out


def _one_int(value, state, name):
    if value is None or value is NA:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        if value < _INT_MIN or value > _INT_MAX:
            if value == -2147483648:
                return None
            state.range_na = True
            return None
        return value
    if isinstance(value, float):
        if (
            math.isnan(value)
            or math.isinf(value)
            or value <= -2147483648.0
            or value >= 2147483648.0
        ):
            state.range_na = True
            return None
        return int(math.trunc(value))
    if isinstance(value, str):
        return _parse_int(value, state)
    raise ValueError(
        f"argument `{name}` should be an integer vector (or an object coercible to)"
    )


def _parse_int(text, state):
    token = text.strip()
    if token == "":
        state.parse_na = True
        return None
    try:
        number = float(token)
    except ValueError:
        state.parse_na = True
        return None
    if (
        math.isnan(number)
        or math.isinf(number)
        or number <= -2147483648.0
        or number >= 2147483648.0
    ):
        state.range_na = True
        return None
    return int(math.trunc(number))


def _as_strings(value, name):
    if value is None:
        return []
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes)):
        return [_one_string(item, name) for item in value]
    return [_one_string(value, name)]


def _one_string(value, name):
    if value is None or value is NA:
        return NA
    if isinstance(value, str):
        return _strip_bom(value)
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        return _format_double(value)
    raise ValueError(
        f"argument `{name}` should be a character vector (or an object coercible to)"
    )


def _strip_bom(text):
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def _format_double(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


stri_sub_all_replace = stri_sub_replace_all
