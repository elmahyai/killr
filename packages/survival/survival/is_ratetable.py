"""Verify that an object is of class ratetable."""

from __future__ import annotations

from typing import Any

from survival._coxsurv import _inherits

_DATE_CLASSES = frozenset(
    {"Date", "POSIXt", "date", "chron", "POSIXct", "POSIXlt"}
)


def _datecheck(x: Any) -> bool:
    if x is None:
        return False
    klass = getattr(x, "class_", None)
    if klass is None:
        klass = getattr(x, "class", None)
    if klass is None and isinstance(x, dict):
        klass = x.get("class_") or x.get("class")
    if isinstance(klass, str):
        parts = set(klass.split("."))
        return bool(parts & _DATE_CLASSES) or klass in _DATE_CLASSES
    if isinstance(klass, (list, tuple)):
        return bool(_DATE_CLASSES.intersection(klass))
    return False


def _cutpoint_is_null(cp: Any) -> bool:
    if cp is None:
        return True
    if isinstance(cp, (list, tuple)) and len(cp) == 0:
        return True
    return hasattr(cp, "__len__") and not isinstance(cp, (str, bytes)) and len(cp) == 0


def _attribute_names(x: Any) -> list[str]:
    if isinstance(x, dict):
        return list(x.keys())
    names = []
    for key in ("dim", "dimnames", "cutpoints", "type", "factor", "dimid", "class", "class_", "data"):
        if getattr(x, key, None) is not None or (isinstance(x, dict) and key in x):
            names.append(key)
    if hasattr(x, "__dict__"):
        names.extend(k for k in x.__dict__ if k not in names)
    return names


def _get_attr(x: Any, name: str, default=None):
    if isinstance(x, dict):
        return x.get(name, default)
    return getattr(x, name, default)


def _data_length(x: Any) -> int | None:
    data = _get_attr(x, "data")
    if data is not None:
        return len(data)
    if isinstance(x, dict):
        return None
    if hasattr(x, "__len__"):
        return len(x)
    return None


def _dimnames_names(att: dict[str, Any]) -> list[str] | None:
    dimnames = att.get("dimnames")
    if dimnames is None:
        return None
    names = att.get("dimnames_names")
    if names is not None:
        return list(names)
    if isinstance(dimnames, dict):
        return list(dimnames.keys())
    name_attr = getattr(dimnames, "names", None)
    if name_attr is not None:
        return list(name_attr)
    return None


def _dimnames_list(att: dict[str, Any]) -> list[Any]:
    dimnames = att.get("dimnames")
    if dimnames is None:
        return []
    if isinstance(dimnames, dict):
        names = _dimnames_names(att)
        if names is None:
            return list(dimnames.values())
        return [dimnames[name] for name in names]
    return list(dimnames)


def _gather_attributes(x: Any) -> dict[str, Any]:
    if isinstance(x, dict):
        att = {key: value for key, value in x.items() if key not in ("class", "class_", "data")}
    else:
        att = {}
        for key in _attribute_names(x):
            if key in ("class", "class_", "data"):
                continue
            att[key] = _get_attr(x, key)
    dimnames = att.get("dimnames")
    if isinstance(dimnames, dict):
        names = att.get("dimnames_names") or list(dimnames.keys())
        att["dimnames"] = [dimnames[name] for name in names]
        if att.get("dimid") is None:
            att["dimid"] = list(names)
    return att


def _order_ok(values: Any, n: int) -> bool:
    if values is None or _cutpoint_is_null(values):
        return False
    seq = list(values)
    if len(seq) != n:
        return False
    indexed = sorted(range(n), key=lambda i: (float(seq[i]), i))
    return indexed == list(range(n))


def is_ratetable(x: Any, verbose: bool = False) -> bool | list[str]:
    """Return True when x is a valid ratetable object."""
    dlist = ("dim", "dimnames", "cutpoints")
    att = _gather_attributes(x)
    cutpoints = att.get("cutpoints") or []
    is_date = [_datecheck(cp) for cp in cutpoints]
    dimid = _dimnames_names(att)
    if dimid is None:
        dimid = att.get("dimid")

    if not verbose:
        if not _inherits(x, "ratetable"):
            return False
        names = _attribute_names(x) if isinstance(x, dict) else list(att.keys())
        if any(name not in names for name in dlist):
            return False
        if att.get("dimid") is None:
            att["dimid"] = _dimnames_names(att)
        nd = len(att["dim"])
        data_len = _data_length(x)
        if data_len is None:
            return False
        dim_prod = 1
        for value in att["dim"]:
            dim_prod *= int(value)
        if data_len != dim_prod:
            return False
        if dimid is None:
            return False
        if any(item is None or item == "" for item in dimid):
            return False
        dimnames = _dimnames_list(att)
        if not isinstance(dimnames, list) or not isinstance(cutpoints, list):
            return False
        if len(dimnames) != nd or len(cutpoints) != nd:
            return False
        if att.get("type") is not None:
            fac_type = att["type"]
            if len(fac_type) != nd:
                return False
            if any(value not in (1, 2, 3, 4) for value in fac_type):
                return False
            if sum(1 for value in fac_type if value == 4) > 1:
                return False
            if any((value > 2) != is_date[i] for i, value in enumerate(fac_type)):
                return False
            fac = [1 if value == 1 else 0 for value in fac_type]
        elif att.get("factor") is not None:
            fac = [float(value) for value in att["factor"]]
            if any(value != value for value in fac):
                return False
            if any(value < 0 for value in fac):
                return False
            if len(fac) != nd:
                return False
            if sum(1 for value in fac if value > 1) > 1:
                return False
            if any(value == 1 and is_date[i] for i, value in enumerate(fac)):
                return False
        else:
            return False
        if len(att.get("dimid") or []) != nd:
            return False
        for i in range(nd):
            n = int(att["dim"][i])
            if len(dimnames[i]) != n:
                return False
            if fac[i] != 1 and (len(cutpoints[i]) if not _cutpoint_is_null(cutpoints[i]) else 0) != n:
                return False
            if fac[i] != 1 and not _order_ok(cutpoints[i], n):
                return False
            if fac[i] == 1 and not _cutpoint_is_null(cutpoints[i]):
                return False
            if fac[i] > 1 and i < nd - 1:
                return False
        return True

    msg: list[str] = []
    if not _inherits(x, "ratetable"):
        msg.append("wrong class")
    names = _attribute_names(x) if isinstance(x, dict) else list(att.keys())
    for name in dlist:
        if name not in names:
            msg.append(f"missing attribute: {name}")
    if att.get("dimid") is None:
        att["dimid"] = _dimnames_names(att)
    nd = len(att.get("dim") or [])
    data_len = _data_length(x)
    dim_prod = 1
    for value in att.get("dim") or []:
        dim_prod *= int(value)
    if data_len is not None and data_len != dim_prod:
        msg.append("length of the data does not match prod(dim)")
    dimnames = _dimnames_list(att)
    if not isinstance(att.get("dimnames"), (list, dict)):
        msg.append("dimnames is not a list")
    if not isinstance(cutpoints, list):
        msg.append("cutpoints is not a list")
    if len(dimnames) != nd:
        msg.append("wrong length for dimnames")
    dimid_val = att.get("dimid") or []
    if len(dimid_val) != nd:
        msg.append("wrong length for dimid, or dimnames do not have names")
    if any(item == "" for item in dimid_val):
        msg.append("one of the dimnames identifiers is blank")
    if len(cutpoints) != nd:
        msg.append("wrong length for cutpoints")
    type_vec: list[int] | None = None
    if att.get("type") is not None:
        type_vec = [int(value) for value in att["type"]]
        if any(value not in (1, 2, 3, 4) for value in type_vec):
            msg.append("type attribute must be 1, 2, 3, or 4")
        if len(type_vec) != nd:
            msg.append("wrong length for type attribute")
        else:
            for i, value in enumerate(type_vec):
                if value > 2 and not is_date[i]:
                    msg.append(
                        f"type[{i + 1}] is 3 or 4 but the cutpoint is not one of the date types"
                    )
                if value < 3 and is_date[i]:
                    msg.append(
                        f"type[{i + 1}] is numeric or factor but the cutpoint is a date"
                    )
        if sum(1 for value in type_vec if value == 4) > 1:
            msg.append("two dimenesions idenitied as US ratetable years")
    elif att.get("factor") is not None:
        fac = [float(value) for value in att["factor"]]
        if any(value != value for value in fac):
            msg.append("illegal 'factor' attribute of NA")
        if any(value < 0 for value in fac):
            msg.append("illegal 'factor' attribute of <0")
        if len(fac) != nd:
            msg.append("wrong length for factor")
        type_vec = [1 * (value == 1) + 2 * (value == 0) + 4 * (value > 1) for value in fac]
        if sum(1 for value in fac if value > 1) > 1:
            msg.append("two dimenesions idenitied as US ratetable years")
    else:
        msg.append("missing the 'type' attribute")
    if type_vec is not None:
        for i in range(nd):
            n = int(att["dim"][i])
            if len(dimnames[i]) != n:
                msg.append(f"dimname {i + 1} is the wrong length")
            if type_vec[i] > 1:
                cp_len = len(cutpoints[i]) if not _cutpoint_is_null(cutpoints[i]) else 0
                if cp_len != n:
                    msg.append(f"wrong length for cutpoints {i + 1}")
                elif not _order_ok(cutpoints[i], n):
                    msg.append(f"unsorted cutpoints for dimension {i + 1}")
            if type_vec[i] == 1 and not _cutpoint_is_null(cutpoints[i]):
                msg.append(
                    f"attribute type[{i + 1}] is continuous; cutpoint should be null"
                )
            if att.get("fac") is not None and type_vec[i] == 4 and i < nd - 1:
                msg.append("only the last dimension can be interpolated")
    if not msg:
        return True
    return msg
