"""The magrittr pipe, re-exported.

modelr's %>% is that pipe. Python calls it pipe().
"""

from __future__ import annotations

import sys
from pathlib import Path


def _pipe():
    try:
        from magrittr.pipe import pipe as impl
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "magrittr"))
        from magrittr.pipe import pipe as impl
    return impl


def pipe(value, *steps):
    return _pipe()(value, *steps)
