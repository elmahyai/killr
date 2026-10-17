"""R-level checks that are not a direct C call: files, classes, functions, dates."""

from __future__ import annotations

import os
import re
from datetime import date as Date
from datetime import datetime, timezone

from .qassert import qassert, qtest
from .rtypes import (
    NA,
    CheckError,
    Environment,
    Formula,
    Function,
    R6,
    Vec,
    guess_type,
    inherits,
    inherits_which,
    is_na_scalar,
    is_null,
    message,
    os_name,
    rclass,
    wrap,
    xlength,
)
from . import checks as C


def _first_true(flags) -> int | None:
    for i, flag in enumerate(flags):
        if flag:
            return i
    return None


def checkAccess(x, access=""):
    qassert(access, "S1", var_name="access")
    text = wrap(access).data[0]
    if text == "":
        return True
    letters = list(text)
    if len(letters) != len(set(letters)) or any(item not in {"r", "w", "x"} for item in letters):
        raise CheckError("Access pattern invalid, allowed are 'r', 'w' and 'x'")
    paths = list(wrap(x).data)
    is_win = os.name == "nt"
    is_root = (not is_win) and hasattr(os, "geteuid") and os.geteuid() == 0
    if "r" in letters or is_root:
        bad = _first_true([not os.access(path, os.R_OK) for path in paths])
        if bad is not None:
            return message("'%s' not readable", paths[bad])
    if not is_win:
        if "w" in letters or is_root:
            bad = _first_true([not os.access(path, os.W_OK) for path in paths])
            if bad is not None:
                return message("'%s' not writeable", paths[bad])
        if "x" in letters:
            bad = _first_true([not os.access(path, os.X_OK) for path in paths])
            if bad is not None:
                return message("'%s' not executable", paths[bad])
    return True


def checkFileExists(x, access="", extension=None):
    if not qtest(x, "S+"):
        return "No file provided"
    paths = list(wrap(x).data)
    bad = _first_true([os.path.isdir(path) for path in paths])
    if bad is not None:
        return message("File expected, but directory in place: '%s'", paths[bad])
    bad = _first_true([not os.path.exists(path) for path in paths])
    if bad is not None:
        return message("File does not exist: '%s'", paths[bad])
    access_hit = checkAccess(x, access)
    if access_hit is not True:
        return access_hit
    return _file_extension(paths, extension)


def _file_extension(paths, extension):
    if extension is None:
        return True
    qassert(extension, "S+", var_name="extension")
    suffixes = [item.lower() for item in wrap(extension).data]
    ok = []
    for path in paths:
        lowered = path.lower()
        ok.append(any(lowered.endswith(suffix) for suffix in suffixes))
    if not all(ok):
        bad = ok.index(False)
        return message(
            "File extension must be in {'%s'} (case insensitive), but file name is '%s'",
            "','".join(wrap(extension).data),
            paths[bad],
        )
    return True


def checkDirectoryExists(x, access=""):
    if not qtest(x, "S+"):
        return "No directory provided"
    paths = list(wrap(x).data)
    bad = _first_true([not os.path.exists(path) for path in paths])
    if bad is not None:
        return message("Directory '%s' does not exist", paths[bad])
    bad = _first_true([not os.path.isdir(path) for path in paths])
    if bad is not None:
        return message("Directory expected, but file in place: '%s'", paths[bad])
    return checkAccess(x, access)


def checkPathForOutput(x, overwrite=False, extension=None):
    if not qtest(x, "S+"):
        return "No path provided"
    qassert(overwrite, "B1", var_name="overwrite")
    paths = [os.path.abspath(path) for path in wrap(x).data]
    parents = [os.path.dirname(path) or "." for path in paths]
    bad = _first_true([not os.path.isdir(path) for path in parents])
    if bad is not None:
        return message("Path to file (dirname) does not exist: '%s' of '%s'", parents[bad], paths[bad])
    existing = [i for i, path in enumerate(paths) if os.path.exists(path)]
    if existing:
        if C._flag(overwrite, "overwrite"):
            parent_hit = checkAccess(_as_character(parents), "w")
            if parent_hit is not True:
                return parent_hit
            return checkAccess(_as_character([paths[i] for i in existing]), "rw")
        return message("File at path already exists: '%s'", paths[existing[0]] if len(existing) == 1 else paths[existing[0]])
    if extension is not None:
        qassert(extension, "S1", var_name="extension")
        suffix = "." + wrap(extension).data[0]
        if any(not path.endswith(suffix) for path in paths):
            return message("File must have extension '%s'", suffix)
    return checkAccess(_as_character(parents), "w")


def _as_character(values):
    return Vec("character", list(values))


def checkClass(x, classes, ordered=False, null_ok=False):
    qassert(classes, "S+", var_name="classes")
    qassert(ordered, "B1", var_name="ordered")
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj) and C._flag(null_ok, "null.ok"):
        return True
    wanted = list(wrap(classes).data)
    positions = inherits_which(obj, wanted)
    missing = [i for i, pos in enumerate(positions) if pos == 0]
    have = rclass(obj)
    if missing:
        w = missing[0]
        plural = "es" if len(have) > 1 else ""
        return message(
            "Must inherit from class '%s', but has class%s '%s'",
            wanted[w],
            plural,
            "','".join(have),
        )
    if C._flag(ordered, "ordered"):
        bad = [i for i, pos in enumerate(positions) if pos != i + 1]
        if bad:
            w = bad[0]
            plural = "es" if len(have) > 1 else ""
            return message(
                "Must have class '%s' in position %i, but has class%s '%s'",
                wanted[w],
                w + 1,
                plural,
                "','".join(have),
            )
    return True


def checkMultiClass(x, classes, null_ok=False):
    qassert(classes, "S+", var_name="classes")
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj) and C._flag(null_ok, "null.ok"):
        return True
    wanted = list(wrap(classes).data)
    if not inherits(obj, wanted):
        have = rclass(obj)
        plural = "es" if len(have) > 1 else ""
        return message(
            "Must inherit from class '%s', but has class%s '%s'",
            "'/'".join(wanted),
            plural,
            "','".join(have),
        )
    return True


def checkFunction(x, args=None, ordered=False, nargs=None, null_ok=False):
    qassert(null_ok, "B1", var_name="null.ok")
    obj = x if isinstance(x, Function) else wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be a function, not 'NULL'"
    if not isinstance(obj, Function):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return message("Must be a function%s, not '%s'", suffix, guess_type(obj))
    if args is not None:
        qassert(args, "S", var_name="args")
        wanted = list(wrap(args).data)
        formals = list(obj.formals)
        if len(wanted) == 0:
            if formals:
                return "May not have any arguments"
            return True
        qassert(ordered, "B1", var_name="ordered")
        if C._flag(ordered, "ordered"):
            if len(formals) < len(wanted) or formals[: len(wanted)] != wanted:
                return message("Must have first formal arguments (ordered): %s", ",".join(wanted))
        else:
            missing = [name for name in wanted if name not in formals]
            if missing:
                return message("Must have formal arguments: %s", ",".join(missing))
    if nargs is not None:
        from .asserting import asCount
        count = asCount(nargs)
        have = len([name for name in obj.formals if name != "..."])
        got = count.data[0] if isinstance(count, Vec) else count
        if got != have:
            return message("Must have exactly %i formal arguments, but has %i", got, have)
    return True


def checkFormula(x, null_ok=False):
    obj = wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be a formula, not 'NULL'"
    if not isinstance(obj, Formula):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return message("Must be a formula%s, not %s", suffix, guess_type(obj))
    return True


def checkEnvironment(x, contains=None, null_ok=False):
    if contains is None:
        contains = Vec("character", [])
    qassert(contains, "S", var_name="contains")
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be an environment, not 'NULL'"
    if not isinstance(obj, Environment):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return message("Must be an environment%s, not '%s'", suffix, guess_type(obj))
    names = list(wrap(contains).data)
    if names:
        have = set(obj.bindings)
        for name in names:
            if name not in have:
                return message("Must contain an object with name '%s'", name)
    return True


def checkDate(x, lower=None, upper=None, any_missing=True, all_missing=True, len=None,
              min_len=None, max_len=None, unique=False, null_ok=False):
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be of class 'Date', not 'NULL'"
    if not (isinstance(obj, Vec) and "Date" in obj.klass):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return message("Must be of class 'Date'%s, not '%s'", suffix, guess_type(obj))
    codes = []
    for item in obj.data:
        if item is NA or (isinstance(item, float) and item != item):
            codes.append(NA)
        else:
            codes.append(int(float(item)))
    hit = C.checkInteger(
        Vec("integer", codes, names=obj.names),
        any_missing=any_missing,
        all_missing=all_missing,
        len=len,
        min_len=min_len,
        max_len=max_len,
        unique=unique,
    )
    if hit is not True:
        return hit
    return _date_bounds(obj, lower, upper)


def _as_date(value, name: str) -> Vec:
    obj = wrap(value)
    if isinstance(obj, Vec) and "Date" in obj.klass:
        if xlength(obj) != 1 or is_na_scalar(obj.data[0], obj.mode):
            raise CheckError(f"Argument '{name}' must be a single (non-missing) date")
        return obj
    if isinstance(value, Date) and not isinstance(value, datetime):
        epoch = Date(1970, 1, 1)
        return Vec("double", [float((value - epoch).days)], klass=("Date",))
    if isinstance(obj, Vec) and obj.mode == "double":
        return Vec("double", list(obj.data), klass=("Date",))
    raise CheckError(f"Argument '{name}' must be a single (non-missing) date")


def _date_bounds(obj: Vec, lower, upper):
    if lower is not None:
        bound = _as_date(lower, "lower")
        limit = float(bound.data[0])
        if any(float(item) < limit for item in obj.data if item is not NA):
            return message("Date must be >= %s", _format_date(limit))
    if upper is not None:
        bound = _as_date(upper, "upper")
        limit = float(bound.data[0])
        if any(float(item) > limit for item in obj.data if item is not NA):
            return message("Date must be <= %s", _format_date(limit))
    return True


def _format_date(days: float) -> str:
    moment = datetime.fromtimestamp(0, timezone.utc) + __import__("datetime").timedelta(days=days)
    # Dates are days since 1970-01-01, not timestamps.
    epoch = Date(1970, 1, 1)
    from datetime import timedelta
    return (epoch + timedelta(days=int(days))).isoformat()


def checkNull(x):
    if not is_null(wrap(x)):
        return "Must be NULL"
    return True


def checkTRUE(x, na_ok=False):
    qassert(na_ok, "B1", var_name="na.ok")
    obj = wrap(x)
    if obj.mode == "logical" and xlength(obj) == 1 and obj.data[0] is True:
        return True
    if C._flag(na_ok, "na.ok") and xlength(obj) == 1 and is_na_scalar(obj.data[0], obj.mode):
        return True
    return "Must be TRUE"


def checkFALSE(x, na_ok=False):
    qassert(na_ok, "B1", var_name="na.ok")
    obj = wrap(x)
    if obj.mode == "logical" and xlength(obj) == 1 and obj.data[0] is False:
        return True
    if C._flag(na_ok, "na.ok") and xlength(obj) == 1 and is_na_scalar(obj.data[0], obj.mode):
        return True
    return "Must be FALSE"


def checkScalarNA(x, null_ok=False):
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be a scalar missing value, not 'NULL'"
    atomic = isinstance(obj, Vec) and obj.mode in {"logical", "integer", "double", "complex", "character", "raw"}
    if not atomic or xlength(obj) != 1 or not is_na_scalar(obj.data[0], obj.mode):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return "Must be a scalar missing value" + suffix
    return True


def _and(lhs, rhs):
    return rhs if lhs is True else lhs


def _split_indices(value) -> list[str]:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    else:
        text = "__".join(str(item) for item in value)
    if text == "":
        return []
    return text.split("__")


def checkDataTable(x, key=None, index=None, types=None, any_missing=True, all_missing=True,
                   min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None,
                   ncols=None, row_names=None, col_names=None, null_ok=False):
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be a data.table, not 'NULL'"
    if not (isinstance(obj, Vec) and "data.table" in obj.klass):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return f"Must be a data.table{suffix}, not {guess_type(obj)}"
    frame = C.checkDataFrame(
        obj, types, any_missing, all_missing, min_rows, max_rows, min_cols, max_cols,
        nrows, ncols, row_names, col_names, null_ok=False,
    )
    props = _data_table_props(obj, key, index)
    return _and(frame, props)


def _data_table_props(obj: Vec, key, index):
    if key is not None:
        qassert(key, "S", var_name="key")
        wanted = list(wrap(key).data)
        have = list(getattr(obj, "dt_key", None) or [])
        if set(have) != set(wanted):
            return "Must have primary keys: " + ",".join(str(item) for item in wanted)
    if index is not None:
        qassert(index, "S", var_name="index")
        wanted = list(wrap(index).data)
        have = _split_indices(getattr(obj, "dt_index", None))
        if set(have) != set(wanted):
            return "Must have secondary keys (indices): " + ",".join(str(item) for item in wanted)
    return True


def _is_r6(obj) -> bool:
    if isinstance(obj, R6):
        return True
    names = getattr(obj, "r_class", None)
    if names and "R6" in names:
        return True
    return isinstance(obj, Vec) and "R6" in obj.klass


def checkR6(x, classes=None, ordered=False, cloneable=None, public=None, private=None, null_ok=False):
    obj = x if isinstance(x, R6) else wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be an R6 class, not 'NULL'"
    if not _is_r6(obj):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return f"Must be an R6 class{suffix}, not {guess_type(obj)}"
    wanted = ["R6"] if classes is None else [*list(wrap(classes).data), "R6"]
    hit = checkClass(obj, wanted, ordered=ordered)
    props = _r6_props(obj, cloneable, public, private)
    return _and(hit, props)


def _r6_props(obj, cloneable, public, private):
    if cloneable is not None:
        qassert(cloneable, "B1", var_name="cloneable")
        flag = cloneable if isinstance(cloneable, bool) else bool(wrap(cloneable).data[0])
        has_clone = "clone" in getattr(obj, "public", {})
        if flag and not has_clone:
            return "Must be cloneable"
        if not flag and has_clone:
            return "May not be cloneable"
    if public is not None:
        qassert(public, "S", var_name="public")
        have = set(getattr(obj, "public", {}))
        for name in wrap(public).data:
            if name not in have:
                return f"Must provide the public slot '{name}'"
    if private is not None:
        qassert(private, "S", var_name="private")
        have = set(getattr(obj, "private", {}) or {})
        for name in wrap(private).data:
            if name not in have:
                return f"Must provide the private slot '{name}'"
    return True


def checkTibble(x, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None,
                min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None,
                col_names=None, null_ok=False):
    qassert(null_ok, "B1", var_name="null.ok")
    obj = wrap(x)
    if is_null(obj):
        if C._flag(null_ok, "null.ok"):
            return True
        return "Must be a tibble, not 'NULL'"
    if not (isinstance(obj, Vec) and "tbl_df" in obj.klass):
        suffix = " (or 'NULL')" if C._flag(null_ok, "null.ok") else ""
        return f"Must be a tibble{suffix}, not {guess_type(obj)}"
    return C.checkDataFrame(
        obj, types, any_missing, all_missing, min_rows, max_rows, min_cols, max_cols,
        nrows, ncols, row_names, col_names, null_ok,
    )


def checkOS(os):
    from .asserting import matchArg
    ok = matchArg(os, ["windows", "mac", "linux", "solaris"], several_ok=True)
    names = list(ok.data) if isinstance(ok, Vec) else list(ok)
    if os_name() not in names:
        return message("OS must be %s", " or ".join(names))
    return True


def anyMissing(x):
    from .rtypes import any_missing
    return any_missing(wrap(x))


def allMissing(x):
    from .rtypes import all_missing
    return all_missing(wrap(x))


def anyNaN(x):
    from .rtypes import any_nan
    return any_nan(wrap(x))


def anyInfinite(x):
    from .rtypes import any_infinite
    return any_infinite(wrap(x))


def wf(x, use_names=True):
    return _which(x, use_names, last=False)


def wl(x, use_names=True):
    return _which(x, use_names, last=True)


def _which(x, use_names, last: bool):
    obj = wrap(x)
    if not (isinstance(obj, Vec) and obj.mode == "logical"):
        raise CheckError("Argument 'x' must be logical")
    flag = wrap(use_names)
    if not (isinstance(flag, Vec) and flag.mode == "logical" and xlength(flag) == 1):
        raise CheckError("Argument 'use.names' must be a flag")
    indexes = [i for i, item in enumerate(obj.data) if item is not NA and item]
    if not indexes:
        return Vec("integer", [])
    pick = indexes[-1] if last else indexes[0]
    names = None
    if flag.data[0] and obj.names:
        names = [obj.names[pick]]
    return Vec("integer", [pick + 1], names=names)


def coalesce(lhs, rhs):
    if lhs is None or is_null(lhs):
        return rhs
    return lhs
