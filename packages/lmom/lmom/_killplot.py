"""Load a killplot function that is not in the killplot package's __init__.

The repository root holds a folder named ``killplot`` that shadows the
installed package, so both import paths are tried.
"""

from __future__ import annotations

import importlib


def killplot_function(module: str, name: str):
    try:
        mod = importlib.import_module(f"killplot.{module}")
    except ImportError:
        mod = importlib.import_module(f"killplot.killplot.{module}")
    return getattr(mod, name)
