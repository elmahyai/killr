"""Defunct tools functions."""

from __future__ import annotations

from typing import Any


def _defunct(name: str, replacement: str) -> None:
    raise RuntimeError(
        f"'{name}' is defunct.\n"
        f"Use '{replacement}' instead.\n"
        'See help("Defunct")'
    )


def get_dep_list(*_args: Any, **_kwargs: Any) -> None:
    """getDepList was removed."""
    _defunct("getDepList", "dependsOnPkgs() or package_dependencies()")


def pkg_depends(*_args: Any, **_kwargs: Any) -> None:
    """pkgDepends was removed."""
    _defunct("pkgDepends", "package_dependencies()")


def vignette_depends(*_args: Any, **_kwargs: Any) -> None:
    """vignetteDepends was removed."""
    _defunct("vignetteDepends", "vignetteInfo()$depends or package_dependencies()")


def package_dependencies(*_args: Any, **_kwargs: Any) -> None:
    """package.dependencies was removed. The replacement is package_dependencies."""
    _defunct("package.dependencies", "package_dependencies")


def install_found_depends(*_args: Any, **_kwargs: Any) -> None:
    """installFoundDepends was removed and has no replacement."""
    raise RuntimeError("'installFoundDepends' is defunct.\nSee help(\"Defunct\")")
