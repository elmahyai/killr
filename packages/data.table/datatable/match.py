"""chmatch, %chin%, and %notin%."""

from __future__ import annotations

from datatable._util import NA_INTEGER, as_sequence, is_na, r_type


def _key(value, kind: str):
    if is_na(value):
        return ("na", kind)
    if kind == "double":
        return ("v", float(value))
    if kind == "integer":
        return ("v", int(value))
    if kind == "logical":
        return ("v", bool(value))
    return ("v", str(value))


def _member_map(table, kind: str):
    found = {}
    for index, item in enumerate(table, start=1):
        key = _key(item, kind)
        if key not in found:
            found[key] = index
    return found


def chmatch(x, table, nomatch=None):
    """First match of each string in table. nomatch defaults to NA."""
    xs = [None if is_na(item) else str(item) for item in as_sequence(x)]
    ts = [None if is_na(item) else str(item) for item in as_sequence(table)]
    if nomatch is None:
        missing = None
    else:
        missing = int(nomatch)
        if missing == NA_INTEGER:
            missing = None
    found = {}
    for index, item in enumerate(ts, start=1):
        if item not in found:
            found[item] = index
    out = []
    for item in xs:
        if item in found:
            out.append(found[item])
        else:
            out.append(missing)
    return out


def chin(x, table):
    """%chin%. Character membership. NA matches NA, and a miss is FALSE."""
    xs = [None if is_na(item) else str(item) for item in as_sequence(x)]
    present = set(None if is_na(item) else str(item) for item in as_sequence(table))
    return [item in present for item in xs]


def notin(x, table):
    """%notin%. TRUE when x is not in table. NA matches NA."""
    xs = as_sequence(x)
    ts = as_sequence(table)
    if xs and ts and all(isinstance(item, str) or is_na(item) for item in xs + ts):
        return [not item for item in chin(xs, ts)]
    kind = "character"
    for item in xs + ts:
        if is_na(item):
            continue
        kind = r_type(item)
        break
    found = _member_map(ts, kind)
    return [_key(item, kind) not in found for item in xs]
