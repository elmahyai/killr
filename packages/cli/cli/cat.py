"""cat helpers. They write to stdout and also return the text they wrote."""

from __future__ import annotations

import sys

from cli.boxes import boxx
from cli.layout import _apply_style, rule
from cli.symbol import symbol


def cat_line(*parts, col=None, background_col=None, file=None) -> str:
    """Paste parts the way paste0 does, then write a trailing newline."""

    if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
        text = "\n".join("" if part is None else str(part) for part in parts[0])
    else:
        text = "".join("" if part is None else str(part) for part in parts)
    text = _apply_style(text, col)
    text = _apply_style(text, background_col, bg=True)
    written = text + "\n"
    target = sys.stdout if file is None else file
    target.write(written)
    return written


def cat_bullet(*parts, col=None, background_col=None, bullet="bullet", bullet_col=None, file=None) -> str:
    """Print one bullet per line."""

    if len(parts) == 1 and isinstance(parts[0], (list, tuple)):
        lines = ["" if part is None else str(part) for part in parts[0]]
    else:
        lines = ["".join("" if part is None else str(part) for part in parts)]
    lines = _apply_style(lines, col)
    mark = _apply_style(symbol[bullet], bullet_col)
    shown = [f"{mark} {line}" for line in lines]
    return cat_line(shown, background_col=background_col, file=file)


def cat_boxx(*args, file=None, **kwargs) -> str:
    """Print a box."""

    return cat_line(boxx(*args, **kwargs), file=file)


def cat_rule(*args, file=None, **kwargs) -> str:
    """Print a rule."""

    return cat_line(rule(*args, **kwargs), file=file)
