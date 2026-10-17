"""Extract specials indexing from an R-style terms object."""

from __future__ import annotations

from typing import Any


def _attr(tt: Any, name: str) -> Any:
    if isinstance(tt, dict):
        return tt.get(name)
    return getattr(tt, name, None)


def _special_indices(tt: Any, special: str) -> list[int]:
    specials = _attr(tt, "specials")
    if specials is None:
        return []
    if isinstance(specials, dict):
        spc = specials.get(special)
    else:
        spc = getattr(specials, special, None)
    if spc is None:
        return []
    if isinstance(spc, int):
        return [spc]
    return [int(value) for value in spc]


def _factors_matrix(tt: Any) -> tuple[list[list[int]], list[str], list[str]]:
    facs = _attr(tt, "factors")
    if isinstance(facs, dict):
        matrix = facs["matrix"]
        rownames = list(facs["rownames"])
        colnames = list(facs["colnames"])
        return matrix, rownames, colnames
    rownames = list(getattr(facs, "rownames", []))
    colnames = list(getattr(facs, "colnames", []))
    if hasattr(facs, "tolist"):
        matrix = facs.tolist()
    else:
        matrix = [list(row) for row in facs]
    return matrix, rownames, colnames


def _match(values: list[int], table: list[int], *, nomatch: int = 0) -> list[int]:
    out: list[int] = []
    for value in values:
        found = nomatch
        for index, item in enumerate(table):
            if value == item:
                found = index + 1
                break
        out.append(found)
    return out


def _order_table(order: int | list[int] | tuple[int, ...]) -> list[int]:
    if isinstance(order, (list, tuple)):
        return [int(value) for value in order]
    return [int(order)]


def untangle_specials(
    tt: Any,
    special: str,
    order: int | list[int] | tuple[int, ...] = 1,
) -> dict[str, list[int] | list[str]]:
    """Return variable names and term indices involving a terms special."""
    spc = _special_indices(tt, special)
    if not spc:
        return {"vars": [], "terms": []}

    matrix, rownames, _colnames = _factors_matrix(tt)
    spc_rows = [matrix[index - 1] for index in spc]
    ff = [sum(row[col] for row in spc_rows) for col in range(len(matrix[0]))]

    response = int(_attr(tt, "response"))
    order_attr = [int(value) for value in _attr(tt, "order")]
    matched = _match(order_attr, _order_table(order), nomatch=0)
    terms = [index + 1 for index, (total, hit) in enumerate(zip(ff, matched)) if total and hit]

    out: dict[str, list[int] | list[str]] = {
        "vars": [rownames[index - 1] for index in spc],
        "tvar": [index - response for index in spc],
        "terms": terms,
    }
    if len(spc) == 1:
        out["tvar"] = out["tvar"][0]  # type: ignore[assignment]
    return out
