"""Session defaults for MCLUST, matching ``mclust.options``."""

from __future__ import annotations

import copy
import sys
from typing import Any

from mclust.em_control import _format_atom

__all__ = ["mclust_options"]

_BIC_PLOT_SYMBOLS = {
    "EII": 17,
    "VII": 2,
    "EEI": 16,
    "EVI": 10,
    "VEI": 13,
    "VVI": 1,
    "EEE": 15,
    "VEE": 8,
    "EVE": 5,
    "VVE": 9,
    "EEV": 12,
    "VEV": 7,
    "EVV": 14,
    "VVV": 0,
    "E": 17,
    "V": 2,
}

_BIC_PLOT_COLORS = {
    "EII": "gray",
    "VII": "black",
    "EEI": "#218B21",
    "EVI": "#41884F",
    "VEI": "#508476",
    "VVI": "#58819C",
    "EEE": "#597DC3",
    "VEE": "#5178EA",
    "EVE": "#716EE7",
    "VVE": "#9B60B8",
    "EEV": "#B2508B",
    "VEV": "#C03F60",
    "EVV": "#C82A36",
    "VVV": "#CC0000",
    "E": "gray",
    "V": "black",
}

_DEFAULT = {
    "emModelNames": [
        "EII",
        "VII",
        "EEI",
        "VEI",
        "EVI",
        "VVI",
        "EEE",
        "VEE",
        "EVE",
        "VVE",
        "EEV",
        "VEV",
        "EVV",
        "VVV",
    ],
    "hcModelName": "VVV",
    "hcUse": "SVD",
    "subset": 2000,
    "fillEllipses": False,
    "bicPlotSymbols": copy.deepcopy(_BIC_PLOT_SYMBOLS),
    "bicPlotColors": copy.deepcopy(_BIC_PLOT_COLORS),
    "classPlotSymbols": [
        16,
        0,
        17,
        3,
        15,
        4,
        1,
        8,
        2,
        7,
        5,
        9,
        6,
        10,
        11,
        18,
        12,
        13,
        14,
    ],
    "classPlotColors": [
        "dodgerblue2",
        "red3",
        "green3",
        "slateblue",
        "darkorange",
        "skyblue1",
        "violetred4",
        "forestgreen",
        "steelblue4",
        "slategrey",
        "brown",
        "black",
        "darkseagreen",
        "darkgoldenrod3",
        "olivedrab",
        "royalblue",
        "tomato4",
        "cyan2",
        "springgreen2",
    ],
    "warn": False,
}

_MCLUST = copy.deepcopy(_DEFAULT)


def mclust_options(*args: Any, **kwargs: Any) -> Any:
    """Set or retrieve default values used by MCLUST."""
    global _MCLUST
    if len(args) == 0 and len(kwargs) == 0:
        return _snapshot(_MCLUST)

    if len(args) == 1 and len(kwargs) == 0:
        arg = args[0]
        if isinstance(arg, str):
            return _MCLUST[arg]
        if isinstance(arg, dict):
            kwargs = arg
        else:
            raise ValueError(f'invalid argument: "{arg}"')

    if len(kwargs) == 0:
        return _snapshot(_MCLUST)

    if any(name is None or name == "" for name in kwargs):
        raise ValueError("options must be given by name")

    current = copy.deepcopy(_MCLUST)
    for name, value in kwargs.items():
        current[name] = value
    _MCLUST = current
    return _snapshot(_MCLUST)


def _snapshot(state: dict[str, Any]) -> _OptionsList:
    return _OptionsList(copy.deepcopy(state))


class _OptionsList(dict):
    """The named list ``mclust.options`` returns when setting options."""

    def __str__(self) -> str:
        lines: list[str] = []
        for name in _DEFAULT:
            if name not in self:
                continue
            lines.append("$" + name)
            lines.append("[1] " + _format_option_value(self[name]))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _format_option_value(value: Any) -> str:
    if isinstance(value, bool):
        return _format_atom(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _format_atom(float(value))
    if isinstance(value, str):
        return _format_atom(value)
    if isinstance(value, dict):
        names = list(value.keys())
        if all(isinstance(item, str) for item in names):
            ordered = [value[name] for name in names]
            if all(isinstance(item, int) and not isinstance(item, bool) for item in ordered):
                return " ".join(str(item) for item in ordered)
            if all(isinstance(item, str) for item in ordered):
                return " ".join(f'"{item}"' for item in ordered)
        return " ".join(_format_atom(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return ""
        if all(isinstance(item, str) for item in value):
            return " ".join(f'"{item}"' for item in value)
        if all(isinstance(item, int) and not isinstance(item, bool) for item in value):
            return " ".join(str(item) for item in value)
        return " ".join(_format_atom(item) for item in value)
    return str(value)


def _format_scalar_line(value: Any) -> str:
    if isinstance(value, bool):
        text = "TRUE" if value else "FALSE"
    elif isinstance(value, int) and not isinstance(value, bool):
        text = str(value)
    elif isinstance(value, float):
        text = _format_atom(value)
    else:
        text = str(value)
    return "[1] " + text


def print_mclust_option(value: Any) -> None:
    """Print one option the way R prints ``mclust.options("name")``."""
    sys.stdout.write(_format_scalar_line(value) + "\n")
