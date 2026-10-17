"""Low-level lattice settings, matching ``lattice.options`` in lattice 0.23-1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

_FUNCTION = object()
_GROB = object()

_DATA_PATH = Path(__file__).with_name("_lattice_options_data.json")


def _convert_loaded(value: Any) -> Any:
    if isinstance(value, dict):
        if value == {"__function__": True}:
            return _FUNCTION
        if value == {"__grob__": True}:
            return _GROB
        return {key: _convert_loaded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_convert_loaded(item) for item in value]
    return value


def _load_defaults() -> dict[str, Any]:
    with _DATA_PATH.open(encoding="utf-8") as handle:
        return _convert_loaded(json.load(handle))


def _modify_list(base: dict[str, Any] | None, updates: dict[str, Any]) -> dict[str, Any]:
    if base is None:
        base = {}
    merged = copy.deepcopy(base)
    for key, value in updates.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _modify_list(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
        if key in merged and merged[key] is None:
            del merged[key]
    return merged


_lattice_options: dict[str, Any] = _load_defaults()


def lattice_options(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Get or set lattice options the way ``lattice.options`` does in R."""
    global _lattice_options

    entries: list[tuple[str | None, Any]] = []
    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
        entries = [(key, value) for key, value in args[0].items()]
    else:
        for arg in args:
            if isinstance(arg, str):
                entries.append((None, arg))
            elif isinstance(arg, dict):
                entries.extend((key or None, value) for key, value in arg.items())
            else:
                raise TypeError("lattice.options arguments must be names or a list")
        entries.extend(kwargs.items())

    old = _lattice_options
    if not entries:
        return copy.deepcopy(old)

    if len(entries) == 1 and entries[0][0] is None and isinstance(entries[0][1], dict):
        entries = [(key, value) for key, value in entries[0][1].items()]

    if all(name is None for name, _ in entries):
        keys = [str(value) for _, value in entries]
        return {key: copy.deepcopy(old[key]) for key in keys if key in old}

    nm: list[str] = []
    is_named: list[bool] = []
    new: dict[str, Any] = {}
    for name, value in entries:
        if name is None:
            key = str(value)
            nm.append(key)
            new[key] = value
            is_named.append(False)
        else:
            nm.append(name)
            new[name] = value
            is_named.append(True)

    ret_val = {key: copy.deepcopy(old[key]) for key in nm if key in old}
    set_keys = [key for key, named in zip(nm, is_named, strict=True) if named]
    if set_keys:
        _lattice_options = _modify_list(old, {key: new[key] for key in set_keys})
    return ret_val
