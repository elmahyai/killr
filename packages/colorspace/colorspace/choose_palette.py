"""Graphical palette chooser dispatch (colorspace 2.1-4)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from colorspace.diverging_hcl import diverging_hcl

_GUI_CHOICES = ("tcltk", "shiny")
PaletteFn = Callable[..., list[str] | Any]


def _match_gui(gui: str) -> str:
    if gui not in _GUI_CHOICES:
        opts = ", ".join(f'"{choice}"' for choice in _GUI_CHOICES)
        raise ValueError(f"'arg' should be one of {opts}")
    return gui


def choose_palette_tcltk(
    pal: PaletteFn = diverging_hcl,
    n: int = 7,
    parent: Any = None,
    **kwargs: Any,
) -> Any:
    raise RuntimeError(
        "choose_palette tcltk GUI is not available in this environment"
    )


def choose_palette_shiny(pal: PaletteFn | None = None, n: int = 7, **kwargs: Any) -> Any:
    raise RuntimeError(
        "choose_palette shiny GUI is not available in this environment"
    )


def choose_palette(
    pal: PaletteFn = diverging_hcl,
    n: int = 7,
    parent: Any = None,
    gui: str = "tcltk",
    **kwargs: Any,
) -> Any:
    gui = _match_gui(gui)
    args: dict[str, Any] = {"pal": pal, "n": n, "parent": parent, **kwargs}
    backend_name = f"choose_palette_{gui}"
    backend = globals()[backend_name]
    return backend(**args)
