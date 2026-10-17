"""diffobj options.

R stores these in ``options()`` under ``diffobj.*``. ``.onLoad`` fills any
name that is not already set. ``gdo`` reads that table and falls back to the
same defaults.
"""

from __future__ import annotations

DEFAULTS: dict[str, object] = {
    "diffobj.context": 2,
    "diffobj.context.auto.min": 1,
    "diffobj.context.auto.max": 10,
    "diffobj.ignore.white.space": True,
    "diffobj.convert.hz.white.space": True,
    "diffobj.strip.sgr": None,
    "diffobj.line.limit": -1,
    "diffobj.pager": "auto",
    "diffobj.pager.mode": "threshold",
    "diffobj.pager.threshold": -1,
    "diffobj.pager.file.keep": False,
    "diffobj.pager.file.path": None,
    "diffobj.less.flags": "R",
    "diffobj.word.diff": True,
    "diffobj.unwrap.atomic": True,
    "diffobj.rds": True,
    "diffobj.hunk.limit": -1,
    "diffobj.mode": "auto",
    "diffobj.silent": False,
    "diffobj.warn": True,
    "diffobj.max.diffs": 50000,
    "diffobj.align": None,
    "diffobj.align.threshold": 0.25,
    "diffobj.align.min.chars": 3,
    "diffobj.align.count.alnum.only": True,
    "diffobj.style": "auto",
    "diffobj.format": "auto",
    "diffobj.interactive": None,
    "diffobj.color.mode": "yb",
    "diffobj.term.colors": None,
    "diffobj.brightness": "neutral",
    "diffobj.tab.stops": 8,
    "diffobj.disp.width": 0,
    "diffobj.palette": None,
    "diffobj.guides": True,
    "diffobj.trim": True,
    "diffobj.html.escape.html.entities": True,
    "diffobj.html.js": None,
    "diffobj.html.css": None,
    "diffobj.sgr.supported": None,
    "diffobj.html.scale": True,
    "diffobj.html.output": "auto",
}

settings: dict[str, object] = dict(DEFAULTS)


def gdo(x: str):
    """Value of ``diffobj.<x>``, or the built-in default when it is unset."""

    if not isinstance(x, str):
        raise TypeError("Argument `x` must be character(1L)")
    key = f"diffobj.{x}"
    if key in settings:
        return settings[key]
    return DEFAULTS.get(key)


def diffobj_set_def_opts() -> dict[str, object]:
    """Put every diffobj option back to its default.

    Returns the values those options had before the reset. A missing name is
    ``None``, which is how ``options()`` reports an unset option.
    """

    previous = {key: settings.get(key) for key in DEFAULTS}
    settings.clear()
    settings.update(DEFAULTS)
    return previous
