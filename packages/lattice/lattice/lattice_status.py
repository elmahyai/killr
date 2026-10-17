"""Internal lattice plot status, matching ``lattice.getStatus`` / ``lattice.setStatus`` in R."""

from __future__ import annotations

from typing import Any

_lattice_status: dict[str, Any] = {}


def _default_lattice_status() -> dict[str, Any]:
    return {"print.more": False, "plot.index": 1}


def _default_prefix_status() -> dict[str, Any]:
    return {
        "current.plot.saved": False,
        "current.plot.multipage": False,
        "current.focus.row": 0,
        "current.focus.column": 0,
        "vp.highlighted": False,
    }


def lattice_get_status(name: str, *, prefix: str | None = None) -> Any:
    if prefix is None:
        return _lattice_status.get(name)
    bucket = _lattice_status.get(prefix)
    if not isinstance(bucket, dict):
        return None
    return bucket.get(name)


def lattice_set_status(
    *,
    prefix: str | None = None,
    clean_first: bool = False,
    **values: Any,
) -> None:
    global _lattice_status
    if clean_first:
        _lattice_status = {}
    if not values:
        return
    if prefix is None:
        _lattice_status.update(values)
        return
    bucket = _lattice_status.get(prefix)
    if not isinstance(bucket, dict):
        bucket = {}
        _lattice_status[prefix] = bucket
    bucket.update(values)


def record_printed_trellis(obj: Any, *, save_object: bool | None = None) -> None:
    """Record a trellis object the way ``print.trellis`` does before drawing."""
    if save_object is None:
        from lattice.lattice_get_option import lattice_get_option

        save_object = bool(lattice_get_option("save.object"))

    lattice_set_status(**_default_lattice_status(), clean_first=True)
    lattice_set_status(**{"plot.index": 0})
    pindex = 1 + int(lattice_get_status("plot.index") or 0)
    prefix = f"plot_{pindex:02g}"
    lattice_set_status(**{"plot.index": pindex, "current.prefix": prefix})
    lattice_set_status(prefix=prefix, **_default_prefix_status())
    if save_object:
        lattice_set_status(
            prefix=prefix,
            **{"current.plot.saved": True, "last.object": obj},
        )
    else:
        lattice_set_status(prefix=prefix, **{"current.plot.saved": False})
