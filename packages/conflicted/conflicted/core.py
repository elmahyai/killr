"""Python-side conflict preferences and search-path inspection.

R's ``conflicted`` works by inspecting attached namespaces and installing an
environment on R's search path.  The routing rule makes that state explicit
in Python: callers register package exports and the attached-package order
with this module, rather than mutating Python's import machinery.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

_packages: dict[str, dict[str, Any]] = {}
_attached: list[str] = []
_preferences: dict[str, tuple[str, ...]] = {}


def set_search_path(
    packages: Mapping[str, Mapping[str, Any]], attached: Iterable[str] | None = None
) -> None:
    """Replace the process-local package registry and attached package order."""
    _packages.clear()
    _packages.update({name: dict(exports) for name, exports in packages.items()})
    _attached[:] = list(packages) if attached is None else list(attached)


def register_package(name: str, exports: Mapping[str, Any], *, attach: bool = False) -> None:
    """Register one package's exported objects for :func:`conflict_scout`."""
    _packages[name] = dict(exports)
    if attach and name not in _attached:
        _attached.append(name)


def conflict_prefer(
    name: str, winner: str, losers: Iterable[str] | None = None, quiet: bool = False
) -> None:
    """Prefer ``winner`` for one function, optionally over selected losers."""
    if not isinstance(name, str) or not name:
        raise TypeError("name must be a non-empty string")
    if not isinstance(winner, str) or not winner:
        raise TypeError("winner must be a non-empty string")
    if losers is not None and isinstance(losers, str):
        losers = [losers]
    if losers is not None and not all(isinstance(item, str) for item in losers):
        raise TypeError("losers must contain strings")
    _preferences[name] = (winner,) + (() if losers is None else tuple(losers))


def _package_names(package: str) -> list[str]:
    if package not in _packages:
        raise KeyError(f"package {package!r} is not registered")
    return sorted(_packages[package])


def _intersect_losers(names: Iterable[str], losers: Iterable[str] | None) -> list[str]:
    names = list(names)
    if losers is None:
        return names
    available = {name for loser in losers for name in _package_names(loser)}
    return [name for name in names if name in available]


def conflict_prefer_all(
    winner: str, losers: Iterable[str] | None = None, quiet: bool = False
) -> None:
    """Prefer every exported object in ``winner``."""
    for name in _intersect_losers(_package_names(winner), losers):
        conflict_prefer(name, winner, losers, quiet=quiet)


def conflict_prefer_matching(
    pattern: str,
    winner: str,
    losers: Iterable[str] | None = None,
    quiet: bool = False,
) -> None:
    """Prefer winner exports whose names match a regular expression."""
    names = [name for name in _package_names(winner) if re.search(pattern, name)]
    for name in _intersect_losers(names, losers):
        conflict_prefer(name, winner, losers, quiet=quiet)


def conflicts_prefer(*calls: Any, _quiet: bool = False) -> None:
    """Register preferences from ``("package", "function")`` specifications.

    A specification may be a dotted string (``"package.function"``), a
    two-item tuple, or a callable carrying ``__module__`` and ``__name__``.
    """
    for call in calls:
        if isinstance(call, str):
            package, separator, name = call.partition(".")
            if not separator or not package or not name or "." in name:
                raise ValueError("arguments must be in form 'package.function'")
        elif isinstance(call, tuple) and len(call) == 2:
            package, name = call
        elif callable(call):
            package, name = call.__module__, call.__name__
        else:
            raise TypeError("arguments must identify package and function")
        conflict_prefer(str(name), str(package), quiet=_quiet)


def conflict_scout(pkgs: Iterable[str] | None = None) -> dict[str, list[str]]:
    """Return conflicts among registered package exports.

    Values preserve the supplied package order.  A preference reduces a
    conflict to its winner followed by any unlisted packages, matching R's
    ``prefs_resolve`` behavior.
    """
    package_names = _attached if pkgs is None else list(pkgs)
    index: dict[str, list[str]] = {}
    for package in package_names:
        for name in _package_names(package):
            index.setdefault(name, []).append(package)
    conflicts = {name: packages for name, packages in index.items() if len(packages) > 1}
    for name, packages in list(conflicts.items()):
        preference = _preferences.get(name)
        if preference:
            winner, *losers = preference
            if winner in packages:
                conflicts[name] = [winner] + [
                    package for package in packages if package not in preference
                ]
    return conflicts


def reset() -> None:
    """Clear registered packages, attached packages, and preferences."""
    _packages.clear()
    _attached.clear()
    _preferences.clear()
