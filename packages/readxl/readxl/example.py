"""Paths of the workbooks shipped with readxl."""

from __future__ import annotations

import os
from pathlib import Path


def _extdata() -> Path:
    return Path(__file__).resolve().parent / "extdata"


def readxl_example(path=None):
    """The example file ``path``, or the list of example names when it is omitted."""

    folder = _extdata()
    if path is None:
        return sorted(name for name in os.listdir(folder) if (folder / name).is_file())
    target = folder / path
    if not target.is_file():
        raise FileNotFoundError(f"no example file named {path}")
    return str(target)


def readxl_progress() -> bool:
    """True only in an interactive session that has not turned the spinner off."""

    return False
