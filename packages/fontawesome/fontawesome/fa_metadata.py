"""Font Awesome asset metadata."""

from __future__ import annotations

from .fa import _ICONS


def _unique(values):
    return list(dict.fromkeys(values))


def fa_metadata() -> dict:
    names = _unique(row["name"] for row in _ICONS)
    full = _unique(row["full_name"] for row in _ICONS)
    far = _unique(row["name"] for row in _ICONS if "far " in row["full_name"])
    fas = _unique(row["name"] for row in _ICONS if "fas " in row["full_name"])
    fab = _unique(row["name"] for row in _ICONS if "fab " in row["full_name"])
    full_far = _unique(row["full_name"] for row in _ICONS if "far " in row["full_name"])
    full_fas = _unique(row["full_name"] for row in _ICONS if "fas " in row["full_name"])
    full_fab = _unique(row["full_name"] for row in _ICONS if "fab " in row["full_name"])
    return {
        "version": "6.5.2",
        "icon_count": len(names),
        "icon_names": names,
        "icon_names_full": full,
        "icon_names_far": far,
        "icon_names_fas": fas,
        "icon_names_fab": fab,
        "icon_names_full_far": full_far,
        "icon_names_full_fas": full_fas,
        "icon_names_full_fab": full_fab,
    }
