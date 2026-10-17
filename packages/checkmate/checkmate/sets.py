"""Set, choice, permutation, and name-comparison checks."""

from __future__ import annotations

from .rtypes import (
    NA,
    CheckError,
    Vec,
    all_missing,
    guess_type,
    is_class_numeric,
    is_na_scalar,
    is_null,
    message,
    wrap,
    xlength,
)


def _collapse_set(values) -> str:
    items = []
    seen = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        items.append("NA" if item is NA else str(item))
    if not items:
        return "{}"
    return "{'" + "','".join(items) + "'}"


def _collapse_array(values) -> str:
    items = ["NA" if item is NA else str(item) for item in values]
    if not items:
        return "[]"
    return "['" + "','".join(items) + "']"


def _set_msg(msg: str, what, *args) -> str:
    text = msg % args if args else msg
    if what is None:
        return text[:1].upper() + text[1:]
    return f"{what[:1].upper() + what[1:]} {text}"


def _same_type(x, y) -> bool:
    if x.mode == y.mode:
        return True
    return is_class_numeric(x) and is_class_numeric(y)


def _match_index(item, choices: Vec):
    if xlength(choices) == 0:
        return None
    if choices.mode in {"double", "integer", "logical"} and not isinstance(item, str):
        for i, choice in enumerate(choices.data):
            if item is NA and choice is NA:
                return i
            if item is NA or choice is NA:
                continue
            if float(item) == float(choice):
                return i
        return None
    for i, choice in enumerate(choices.data):
        if item is NA and choice is NA:
            return i
        if item == choice:
            return i
    return None


def _values(obj):
    if is_null(obj):
        return []
    if isinstance(obj, Vec):
        return list(obj.data)
    return [obj]


def checkChoice(x, choices, null_ok=False, fmatch=False):
    from .qassert import qassert
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj):
        if _flag_ok(null_ok):
            return True
        qassert(choices, "a", var_name="choices")
        return message("Must be a subset of %s, not 'NULL'", _collapse_set(_values(wrap(choices))))
    qassert(choices, "a", var_name="choices")
    from .qassert import qtest
    if not qtest(obj, "a1"):
        return message("Must be element of set %s, but is not atomic scalar", _collapse_set(_values(wrap(choices))))
    chosen = wrap(choices)
    if not _same_type(obj, chosen) and not all_missing(obj):
        return message(
            "Must be element of set %s, but types do not match (%s != %s)",
            _collapse_set(chosen.data),
            _class1(obj),
            _class1(chosen),
        )
    if _match_index(obj.data[0], chosen) is None:
        shown = "NA" if obj.data[0] is NA else str(obj.data[0])
        return message("Must be element of set %s, but is '%s'", _collapse_set(chosen.data), shown)
    return True


def checkSubset(x, choices, empty_ok=True, fmatch=False):
    from .qassert import qassert
    qassert(empty_ok, "B1", var_name="empty.ok")
    obj = wrap(x)
    if xlength(obj) == 0:
        if not _flag_ok(empty_ok):
            return message("Must be a subset of %s, not empty", _collapse_set(_values(wrap(choices))))
        return True
    return _subset(obj, wrap(choices), None)


def _subset(obj, choices: Vec, what) -> str | bool:
    from .qassert import qassert
    qassert(choices, "a", var_name="choices")
    if xlength(choices) == 0:
        if xlength(obj) == 0:
            return True
        return _set_msg("must be a subset of the empty set, i.e. also empty", what)
    if not is_null(obj):
        if not _same_type(obj, choices) and not all_missing(obj):
            return _set_msg("must be a subset of %s, but has different type", what, _collapse_set(choices.data))
        missing = [item for item in obj.data if _match_index(item, choices) is None]
        if missing:
            return _set_msg(
                "must be a subset of %s, but has additional elements %s",
                what,
                _collapse_set(choices.data),
                _collapse_set(missing),
            )
    return True


def checkDisjunct(x, y, fmatch=False):
    from .qassert import qassert
    qassert(x, "a", var_name="x")
    qassert(y, "a", var_name="y")
    return _disjunct(wrap(x), wrap(y), None)


def _disjunct(x: Vec, y: Vec, what) -> str | bool:
    if xlength(x) == 0 or xlength(y) == 0:
        return True
    shared = [item for item in x.data if _match_index(item, y) is not None]
    if shared:
        return _set_msg(
            "must be disjunct from %s, but has elements %s",
            what,
            _collapse_set(y.data),
            _collapse_set(shared),
        )
    return True


def checkSetEqual(x, y, ordered=False, fmatch=False):
    from .qassert import qassert
    qassert(x, "a", var_name="x")
    qassert(y, "a", var_name="y")
    qassert(ordered, "B1", var_name="ordered")
    left, right = wrap(x), wrap(y)
    if _flag_ok(ordered):
        same = (
            _same_type(left, right)
            and xlength(left) == xlength(right)
            and not _ordered_diff(left, right)
        )
        if not same:
            return message("Must be equal to %s, but is %s", _collapse_array(right.data), _collapse_array(left.data))
        return True
    return _set_equal(left, right, None)


def _ordered_diff(left: Vec, right: Vec) -> bool:
    for a, b in zip(left.data, right.data):
        a_na = is_na_scalar(a, left.mode)
        b_na = is_na_scalar(b, right.mode)
        if a_na != b_na:
            return True
        if not a_na and a != b and not (is_class_numeric(left) and float(a) == float(b)):
            return True
    return False


def _set_equal(x: Vec, y: Vec, what) -> str | bool:
    if not _same_type(x, y) and not all_missing(x):
        return _set_msg("Must be setequal to %s, but has different type", what, _collapse_set(y.data))
    extra = [item for item in x.data if _match_index(item, y) is None]
    if extra:
        return _set_msg(
            "must be a permutation of set %s, but has extra elements %s",
            what,
            _collapse_set(y.data),
            _collapse_set(extra),
        )
    missing = [item for item in y.data if _match_index(item, x) is None]
    if missing:
        return _set_msg(
            "must be a set equal to %s, but is missing elements %s",
            what,
            _collapse_set(y.data),
            _collapse_set(missing),
        )
    return True


def checkPermutation(x, y, na_ok=True):
    from .qassert import qassert
    qassert(x, "a", var_name="x")
    qassert(y, "a", var_name="y")
    left, right = wrap(x), wrap(y)
    if left.mode == "raw" or right.mode == "raw":
        raise CheckError("Cannot check permutation on raw vectors")
    if not _same_type(left, right) or xlength(left) != xlength(right):
        return message(
            "Must be permutation of %s, but is %s",
            _collapse_array(right.data),
            _collapse_array(left.data),
        )
    if not _flag_ok(na_ok) and (_any_na(left) or _any_na(right)):
        return "The parameter na.ok is set to FALSE but NAs were found."
    xs = _sort_drop_na(left)
    ys = _sort_drop_na(right)
    if len(xs) != len(ys) or any(a != b for a, b in zip(xs, ys)):
        return message("Must be permutation of %s, but is %s", _collapse_array(ys), _collapse_array(xs))
    return True


def names_compare(obj, subset_of, must_include, permutation_of, identical_to, disjunct_from, what: str):
    from .qassert import qassert
    values = [] if is_null(obj) else list(obj.data)
    current = Vec("character", values)
    if subset_of is not None:
        qassert(subset_of, "S", var_name="subset.of")
        hit = _subset(current, wrap(subset_of), what)
        if hit is not True:
            return hit
    if must_include is not None:
        qassert(must_include, "S", var_name="must.include")
        needed = wrap(must_include)
        missing = [item for item in needed.data if _match_index(item, current) is None]
        if missing:
            return _set_msg(
                "must include the elements %s, but is missing elements %s",
                what,
                _collapse_set(needed.data),
                _collapse_set(missing),
            )
    if permutation_of is not None:
        qassert(permutation_of, "S", var_name="permutation.of")
        unique = []
        for item in wrap(permutation_of).data:
            if item not in unique:
                unique.append(item)
        hit = _set_equal(current, Vec("character", unique), what)
        if hit is not True:
            return hit
    if identical_to is not None:
        qassert(identical_to, "S", var_name="identical.to")
        target = wrap(identical_to)
        if current.data != target.data:
            return _set_msg(
                "must be a identical to set %s, but is %s",
                what,
                _collapse_set(target.data),
                _collapse_set(current.data),
            )
    if disjunct_from is not None:
        qassert(disjunct_from, "S", var_name="disjunct.from")
        hit = _disjunct(current, wrap(disjunct_from), what)
        if hit is not True:
            return hit
    return True


def _flag_ok(value) -> bool:
    obj = wrap(value)
    return bool(obj.data[0])


def _class1(obj) -> str:
    from .rtypes import rclass
    return rclass(obj)[0]


def _any_na(obj: Vec) -> bool:
    return any(is_na_scalar(item, obj.mode) for item in obj.data)


def _sort_drop_na(obj: Vec) -> list:
    kept = [item for item in obj.data if not is_na_scalar(item, obj.mode)]
    return sorted(kept, key=lambda item: (str(type(item)), item))
