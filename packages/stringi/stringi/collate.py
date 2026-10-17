"""Locale-aware comparison and sorting from stringi 1.8.9.

Collation uses ICU through PyICU, the same library the installed package
links. Code-point equality is not collation: it compares the strings after
one leading U+FEFF is removed. Sort, order, rank, unique, and duplicated
use that same stripped text, and the strings they return are stripped.
``stri_sort_key`` keeps a leading U+FEFF and drops only the terminating
NUL from the ICU sort key.

A missing character is :data:`stringi._na.NA`. ``None`` is an empty vector
when it is the whole argument, and a missing element inside a vector. The
string ``"NA"`` is text. Results are lists, in the same shape as the fixed
searchers.
"""

from __future__ import annotations

import math
import warnings

import icu

from stringi._na import NA, is_na
from stringi.length import _character_complex, _character_double, _character_integer
from stringi.opts import stri_opts_collator

_MISSING = object()
_BOM = "\ufeff"
_BAD_SPEC = "incorrect collator option specifier, see ?stri_opts_collator"
_ILLEGAL = "Illegal argument. (U_ILLEGAL_ARGUMENT_ERROR)"
_ROOT_WARNING = (
    "A resource bundle lookup returned a result either from the root "
    "or the default locale."
)
_RECYCLE = "longer object length is not a multiple of shorter object length"
_CACHE: dict[tuple, tuple[object, bool]] = {}


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=4)


def _mode(items: list) -> str:
    if any(item is None or is_na(item) or isinstance(item, str) for item in items):
        return "character"
    if any(isinstance(item, complex) for item in items):
        return "complex"
    if any(isinstance(item, float) for item in items):
        return "double"
    if any(isinstance(item, int) and not isinstance(item, bool) for item in items):
        return "integer"
    return "logical"


def _coerce_one(value: object, mode: str):
    if value is None or is_na(value):
        return NA
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        if mode in ("character", "logical"):
            return "TRUE" if value else "FALSE"
        if mode == "integer":
            return _character_integer(int(value))
        if mode == "double":
            return _character_double(float(value))
        return _character_complex(complex(int(value)))
    if isinstance(value, int):
        if mode in ("character", "integer"):
            return _character_integer(value)
        if mode == "double":
            return _character_double(float(value))
        return _character_complex(complex(value))
    if isinstance(value, float):
        if mode in ("character", "double"):
            return _character_double(value)
        return _character_complex(complex(value))
    if isinstance(value, complex):
        return _character_complex(value)
    raise TypeError


def _prepare(value: object, name: str) -> list:
    """Coerce to a character vector. ``None`` is an empty vector."""

    if value is None:
        return []
    if isinstance(value, range):
        items = list(value)
    elif isinstance(value, (list, tuple)):
        items = list(value)
    elif isinstance(value, (bytes, bytearray)):
        raise ValueError(
            f"argument `{name}` should be a character vector (or an object coercible to)"
        )
    else:
        items = [value]
    if not items:
        return []
    mode = _mode(items)
    try:
        return [_coerce_one(item, mode) for item in items]
    except TypeError:
        raise ValueError(
            f"argument `{name}` should be a character vector (or an object coercible to)"
        ) from None


def _strip_bom(text: str) -> str:
    if text.startswith(_BOM):
        return text[1:]
    return text


def _as_sequence(value: object, name: str, kind: str) -> list:
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"argument `{name}` should be a non-empty vector")
        if len(value) > 1:
            _warn(
                f"argument `{name}` should be a single {kind} value; "
                "only the first element is used"
            )
        return list(value)
    return [value]


def _logical_value(value: object, name: str, allow_na: bool):
    if value is None or is_na(value):
        if allow_na:
            return NA
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            if allow_na:
                return NA
            raise ValueError(f"missing values in argument `{name}` is not supported")
        return value != 0
    raise ValueError(
        f"argument `{name}` should be a logical vector (or an object coercible to)"
    )


def _one_logical(value: object, name: str, allow_na: bool):
    items = _as_sequence(value, name, "logical")
    return _logical_value(items[0], name, allow_na)


def _integer_value(value: object, name: str) -> int:
    if value is None or is_na(value):
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"missing values in argument `{name}` is not supported")
        return int(value)
    raise ValueError(
        f"argument `{name}` should be an integer vector (or an object coercible to)"
    )


def _one_integer(value: object, name: str) -> int:
    items = _as_sequence(value, name, "integer")
    return _integer_value(items[0], name)


def _one_locale(value: object) -> str | None:
    """Locale id, or None for the ICU default."""

    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument `locale` should be a non-empty vector")
        if len(value) > 1:
            _warn(
                "argument `locale` should be a single character string; "
                "only the first element is used"
            )
        value = value[0]
    if value is None:
        return None
    if is_na(value):
        raise ValueError("missing values in argument `locale` is not supported")
    if isinstance(value, bool):
        text = "TRUE" if value else "FALSE"
    elif isinstance(value, int):
        text = _character_integer(value)
    elif isinstance(value, float):
        text = _character_double(value)
    elif isinstance(value, str):
        text = value
    else:
        raise ValueError(
            "argument `locale` should be a character vector (or an object coercible to)"
        )
    text = text.strip(" \t\r\n")
    if text == "":
        return None
    if text[0] in "Cc" and (len(text) == 1 or text[1] == "."):
        return "en_US_POSIX"
    if text[0] == "@":
        default = icu.Locale.getDefault().getName()
        if default and default[0] in "Cc" and (len(default) == 1 or default[1] == "."):
            default = "en_US_POSIX"
        return default + text
    return text


def _merge_opts(opts_collator: object, extra: dict) -> object:
    if not extra:
        return opts_collator
    if opts_collator is None:
        base: dict = {}
    elif is_na(opts_collator) or not isinstance(opts_collator, dict):
        raise ValueError(_BAD_SPEC)
    else:
        base = dict(opts_collator)
    for key in extra:
        if key in base:
            raise TypeError(
                f'formal argument "{key}" matched by multiple actual arguments'
            )
    base.update(extra)
    return stri_opts_collator(**base)


def _settings(opts_collator: object) -> tuple:
    if opts_collator is None or opts_collator == {}:
        return (None, None, None, None, None, None, None, None)
    if is_na(opts_collator) or not isinstance(opts_collator, dict):
        raise ValueError(_BAD_SPEC)
    locale = None
    strength = None
    alternate = None
    french = None
    case_first = None
    case_level = None
    normalization = None
    numeric = None
    for key, raw in opts_collator.items():
        if key == "locale":
            locale = _one_locale(raw)
        elif key == "strength":
            val = _one_integer(raw, "strength")
            if val < 1:
                val = 1
            elif val > 17:
                val = 17
            strength = val - 1
        elif key == "alternate_shifted":
            alternate = bool(_one_logical(raw, "alternate_shifted", False))
        elif key == "french":
            french = bool(_one_logical(raw, "french", False))
        elif key == "uppercase_first":
            flag = _one_logical(raw, "uppercase_first", True)
            if is_na(flag):
                case_first = "off"
            else:
                case_first = "upper" if flag else "lower"
        elif key == "case_level":
            case_level = bool(_one_logical(raw, "case_level", False))
        elif key == "normalization":
            normalization = bool(_one_logical(raw, "normalization", False))
        elif key == "numeric":
            numeric = bool(_one_logical(raw, "numeric", False))
        else:
            _warn(f"incorrect opts_collator setting: '{key}'; ignoring")
    return (
        locale,
        strength,
        alternate,
        french,
        case_first,
        case_level,
        normalization,
        numeric,
    )


def _open_collator(settings: tuple):
    locale, strength, alternate, french, case_first, case_level, normalization, numeric = settings
    if locale is None:
        collator = icu.Collator.createInstance(icu.Locale.getDefault())
        requested = None
    else:
        collator = icu.Collator.createInstance(icu.Locale(locale))
        requested = locale
    root = False
    if requested and requested != "root":
        valid = collator.getLocale(icu.ULocDataLocaleType.VALID_LOCALE).getName()
        if valid in ("", "root"):
            root = True
    attribute = icu.UCollAttribute
    value = icu.UCollAttributeValue
    try:
        if strength is not None:
            collator.setAttribute(attribute.STRENGTH, strength)
        if french is not None:
            collator.setAttribute(
                attribute.FRENCH_COLLATION, value.ON if french else value.OFF
            )
        if alternate is not None:
            collator.setAttribute(
                attribute.ALTERNATE_HANDLING,
                value.SHIFTED if alternate else value.NON_IGNORABLE,
            )
        if case_first == "off":
            collator.setAttribute(attribute.CASE_FIRST, value.OFF)
        elif case_first == "upper":
            collator.setAttribute(attribute.CASE_FIRST, value.UPPER_FIRST)
        elif case_first == "lower":
            collator.setAttribute(attribute.CASE_FIRST, value.LOWER_FIRST)
        if case_level is not None:
            collator.setAttribute(
                attribute.CASE_LEVEL, value.ON if case_level else value.OFF
            )
        if normalization is not None:
            collator.setAttribute(
                attribute.NORMALIZATION_MODE,
                value.ON if normalization else value.OFF,
            )
        if numeric is not None:
            collator.setAttribute(
                attribute.NUMERIC_COLLATION, value.ON if numeric else value.OFF
            )
    except icu.ICUError as exc:
        if exc.getErrorCode() == 1:
            raise ValueError(_ILLEGAL) from exc
        raise
    return collator, root


def _collator(opts_collator: object):
    settings = _settings(opts_collator)
    cached = _CACHE.get(settings)
    if cached is None:
        cached = _open_collator(settings)
        _CACHE[settings] = cached
    collator, root = cached
    if root:
        _warn(_ROOT_WARNING)
    return collator


def _recycle(left: int, right: int) -> int:
    if left <= 0 or right <= 0:
        return 0
    size = left if left >= right else right
    if size % left != 0 or size % right != 0:
        _warn(_RECYCLE)
    return size


def _relate(difference: int, kind: str):
    if kind == "cmp":
        return difference
    if kind == "eq":
        return difference == 0
    if kind == "ne":
        return difference != 0
    if kind == "lt":
        return difference == -1
    if kind == "gt":
        return difference == 1
    if kind == "le":
        return difference != 1
    if kind == "ge":
        return difference != -1
    raise ValueError(kind)


def _compare(e1, e2, opts_collator, extra: dict, kind: str) -> list:
    left = _prepare(e1, "e1")
    right = _prepare(e2, "e2")
    size = _recycle(len(left), len(right))
    if size == 0:
        return []
    code_point = kind in ("code_eq", "code_ne")
    collator = None if code_point else _collator(_merge_opts(opts_collator, extra))
    out = []
    for index in range(size):
        a = left[index % len(left)]
        b = right[index % len(right)]
        if is_na(a) or is_na(b):
            out.append(NA)
            continue
        if code_point:
            same = _strip_bom(a) == _strip_bom(b)
            out.append(same if kind == "code_eq" else not same)
        else:
            out.append(_relate(int(collator.compare(_strip_bom(a), _strip_bom(b))), kind))
    return out


def _keys(collator, texts: list) -> list:
    keys = []
    for text in texts:
        if is_na(text):
            keys.append(None)
        else:
            raw = collator.getSortKey(text)
            if raw.endswith(b"\x00"):
                raw = raw[:-1]
            keys.append(raw)
    return keys


def _order_indices(keys: list, decreasing: bool, na_mode) -> list:
    """1-based positions. ``na_mode`` is True, False, or NA."""

    present = []
    missing = []
    for index, key in enumerate(keys):
        if key is None:
            if not is_na(na_mode):
                missing.append(index + 1)
        else:
            present.append(index)
    present.sort(key=lambda index: keys[index], reverse=decreasing)
    ordered = [index + 1 for index in present]
    if na_mode is False:
        return missing + ordered
    if na_mode is True:
        return ordered + missing
    return ordered


def _sorted_strings(texts: list, keys: list, decreasing: bool, na_mode) -> list:
    positions = _order_indices(keys, decreasing, na_mode)
    out = []
    for position in positions:
        text = texts[position - 1]
        out.append(NA if is_na(text) else text)
    return out


def _rank_values(keys: list) -> list:
    present = [index for index, key in enumerate(keys) if key is not None]
    present.sort(key=lambda index: keys[index])
    ranks = [NA] * len(keys)
    first = 1
    minimum = 1
    last = None
    for index in present:
        if first > 1 and keys[index] != keys[last]:
            minimum = first
        ranks[index] = minimum
        last = index
        first += 1
    return ranks


def _seen_key(collator, text: str):
    raw = collator.getSortKey(text)
    if raw.endswith(b"\x00"):
        raw = raw[:-1]
    return raw


def stri_cmp(e1, e2, opts_collator=None, **kwargs):
    """Compare strings with the ICU collator.

    Returns -1, 0, or 1, or NA when either string is missing. 0 means the
    strings are equivalent at the collator's strength, not that their code
    points are equal.
    """

    return _compare(e1, e2, opts_collator, kwargs, "cmp")


stri_compare = stri_cmp


def stri_cmp_eq(e1, e2):
    """Code-point equality. A leading U+FEFF is ignored. NA stays missing."""

    return _compare(e1, e2, None, {}, "code_eq")


def stri_cmp_neq(e1, e2):
    """Code-point inequality. A leading U+FEFF is ignored. NA stays missing."""

    return _compare(e1, e2, None, {}, "code_ne")


def stri_cmp_equiv(e1, e2, opts_collator=None, **kwargs):
    """Collation equivalence. This is not code-point equality."""

    return _compare(e1, e2, opts_collator, kwargs, "eq")


def stri_cmp_nequiv(e1, e2, opts_collator=None, **kwargs):
    """True when the strings are not collation-equivalent."""

    return _compare(e1, e2, opts_collator, kwargs, "ne")


def stri_cmp_lt(e1, e2, opts_collator=None, **kwargs):
    """True when e1 collates before e2."""

    return _compare(e1, e2, opts_collator, kwargs, "lt")


def stri_cmp_gt(e1, e2, opts_collator=None, **kwargs):
    """True when e1 collates after e2."""

    return _compare(e1, e2, opts_collator, kwargs, "gt")


def stri_cmp_le(e1, e2, opts_collator=None, **kwargs):
    """True when e1 collates before or with e2."""

    return _compare(e1, e2, opts_collator, kwargs, "le")


def stri_cmp_ge(e1, e2, opts_collator=None, **kwargs):
    """True when e1 collates after or with e2."""

    return _compare(e1, e2, opts_collator, kwargs, "ge")


def _sort_args(str, decreasing, na_last, opts_collator, extra):
    texts = _prepare(str, "str")
    texts = [NA if is_na(text) else _strip_bom(text) for text in texts]
    decreasing_flag = bool(_one_logical(decreasing, "decreasing", False))
    na_mode = _one_logical(na_last, "na_last", True)
    collator = _collator(_merge_opts(opts_collator, extra))
    return texts, _keys(collator, texts), decreasing_flag, na_mode


def stri_sort(str, decreasing=False, na_last=NA, opts_collator=None, **kwargs):
    """Sort strings with the ICU collator.

    The default ``na_last`` is NA, which drops missing strings. TRUE puts
    them last and FALSE puts them first. A leading U+FEFF is removed from
    each returned string. Numbers are coerced with R's ``as.character``
    before the lexicographic sort.
    """

    texts, keys, decreasing_flag, na_mode = _sort_args(
        str, decreasing, na_last, opts_collator, kwargs
    )
    return _sorted_strings(texts, keys, decreasing_flag, na_mode)


def stri_order(str, decreasing=False, na_last=True, opts_collator=None, **kwargs):
    """1-based stable permutation that sorts ``str``.

    The default keeps missing strings at the end. NA in ``na_last`` drops
    them from the permutation.
    """

    texts, keys, decreasing_flag, na_mode = _sort_args(
        str, decreasing, na_last, opts_collator, kwargs
    )
    return _order_indices(keys, decreasing_flag, na_mode)


def stri_rank(str, opts_collator=None, **kwargs):
    """Minimum ranks from an increasing collation. Missing strings stay missing."""

    texts = [NA if is_na(text) else _strip_bom(text) for text in _prepare(str, "str")]
    keys = _keys(_collator(_merge_opts(opts_collator, kwargs)), texts)
    return _rank_values(keys)


def stri_sort_key(str, opts_collator=None, **kwargs):
    """Bytes of the ICU sort key, without the terminating NUL.

    A leading U+FEFF is part of the key. Missing strings stay missing.
    Ordering these bytes with unsigned comparison matches ``stri_cmp``.
    """

    texts = _prepare(str, "str")
    keys = _keys(_collator(_merge_opts(opts_collator, kwargs)), texts)
    return [NA if key is None else key for key in keys]


def stri_unique(str, opts_collator=None, **kwargs):
    """First occurrence of each collation class, in the original order.

    The first missing string is kept. A leading U+FEFF is removed.
    """

    texts = [NA if is_na(text) else _strip_bom(text) for text in _prepare(str, "str")]
    collator = _collator(_merge_opts(opts_collator, kwargs))
    seen = set()
    out = []
    was_na = False
    for text in texts:
        if is_na(text):
            if not was_na:
                was_na = True
                out.append(NA)
            continue
        key = _seen_key(collator, text)
        if key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _from_last(which: str, from_last, fromLast):
    if fromLast is not _MISSING:
        _warn(
            f"The 'fromLast' argument in {which} is a deprecated alias of "
            "'from_last' and will be removed in a future release of 'stringi'."
        )
        from_last = fromLast
    return bool(_one_logical(from_last, "from_last", False))


def stri_duplicated(str, from_last=False, fromLast=_MISSING, opts_collator=None, **kwargs):
    """True where a collation-equivalent string was already seen.

    Missing strings are equal to each other. ``fromLast`` is the deprecated
    alias of ``from_last``.
    """

    reverse = _from_last("stri_duplicated", from_last, fromLast)
    texts = [NA if is_na(text) else _strip_bom(text) for text in _prepare(str, "str")]
    collator = _collator(_merge_opts(opts_collator, kwargs))
    out = [False] * len(texts)
    seen = set()
    was_na = False
    indexes = range(len(texts) - 1, -1, -1) if reverse else range(len(texts))
    for index in indexes:
        text = texts[index]
        if is_na(text):
            out[index] = was_na
            was_na = True
            continue
        key = _seen_key(collator, text)
        out[index] = key in seen
        seen.add(key)
    return out


def stri_duplicated_any(str, from_last=False, fromLast=_MISSING, opts_collator=None, **kwargs):
    """1-based index of the first repeated string, or 0 when all are unique.

    The result is a one-element list. ``from_last`` walks from the end.
    """

    reverse = _from_last("stri_duplicated_any", from_last, fromLast)
    texts = [NA if is_na(text) else _strip_bom(text) for text in _prepare(str, "str")]
    collator = _collator(_merge_opts(opts_collator, kwargs))
    seen = set()
    was_na = False
    indexes = range(len(texts) - 1, -1, -1) if reverse else range(len(texts))
    found = 0
    for index in indexes:
        text = texts[index]
        if is_na(text):
            if was_na:
                found = index + 1
                break
            was_na = True
            continue
        key = _seen_key(collator, text)
        if key in seen:
            found = index + 1
            break
        seen.add(key)
    return [found]


def s_lt(e1, e2):
    """``%s<%`` with the default collator."""

    return stri_cmp_lt(e1, e2)


def s_le(e1, e2):
    """``%s<=%`` with the default collator."""

    return stri_cmp_le(e1, e2)


def s_gt(e1, e2):
    """``%s>%`` with the default collator."""

    return stri_cmp_gt(e1, e2)


def s_ge(e1, e2):
    """``%s>=%`` with the default collator."""

    return stri_cmp_ge(e1, e2)


def s_eq(e1, e2):
    """``%s==%``, collation equivalence with the default collator."""

    return stri_cmp_equiv(e1, e2)


def s_ne(e1, e2):
    """``%s!=%``, collation inequivalence with the default collator."""

    return stri_cmp_nequiv(e1, e2)


def s_ceq(e1, e2):
    """``%s===%``, code-point equality."""

    return stri_cmp_eq(e1, e2)


def s_cne(e1, e2):
    """``%s!==%``, code-point inequality."""

    return stri_cmp_neq(e1, e2)


stri_lt = s_lt
stri_le = s_le
stri_gt = s_gt
stri_ge = s_ge
stri_eq = s_eq
stri_ne = s_ne
stri_ceq = s_ceq
stri_cne = s_cne
stri_coll = stri_opts_collator
