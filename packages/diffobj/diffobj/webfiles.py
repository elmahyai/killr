"""Paths of the CSS and JavaScript injected into HTML diffs."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def diffobj_css() -> str:
    """Path of the default stylesheet."""

    return (_ROOT / "css" / "diffobj.css").as_posix()


def diffobj_js() -> str:
    """Path of the default script."""

    return (_ROOT / "script" / "diffobj.js").as_posix()
