"""Font Awesome SVG generation."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

_ROOT = Path(__file__).parent
_ICONS = json.loads((_ROOT / "fa_tbl.json").read_text())
_ALIASES = json.loads((_ROOT / "alias_tbl.json").read_text())
_UNITS = {"cm", "mm", "in", "px", "pt", "pc", "em", "ex", "ch", "rem",
          "vw", "vh", "vmin", "vmax", "%"}
_BY_FULL = {row["full_name"]: i for i, row in enumerate(_ICONS)}
_BY_NAME: dict[str, list[int]] = {}
for i, row in enumerate(_ICONS):
    _BY_NAME.setdefault(row["name"], []).append(i)
_ALIASES_BY_NAME = {row["alias"]: row["name"] for row in _ALIASES}


def _index(name: str, prefer_type: str, fail=True) -> int | None:
    if name in _BY_FULL:
        return _BY_FULL[name]
    choices = _BY_NAME.get(name)
    if choices is None and name in _ALIASES_BY_NAME:
        choices = _BY_NAME.get(_ALIASES_BY_NAME[name])
    if not choices:
        if fail:
            raise ValueError(f"The `name` provided ('{name}') does not correspond to a known icon")
        return None
    preferred = [i for i in choices if _ICONS[i]["style"] == prefer_type]
    return preferred[0] if len(preferred) == 1 else choices[0]


def _length(value: str | None) -> tuple[float, str] | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]*\.?[0-9]+[a-z]+", value):
        raise ValueError("Values provided to `height` and `width` must have a numerical value followed by a length unit.")
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)([a-z]+)", value)
    assert match
    number, unit = float(match.group(1)), match.group(2)
    if unit not in _UNITS:
        raise ValueError("The provided CSS length unit is not valid.")
    return number, unit


def _r_round(value: float) -> str:
    # R's round(x, 2), formatted as a short decimal in paste0.
    return str(round(value, 2)).rstrip("0").rstrip(".") if value % 1 else str(int(value))


def fa(name: str, fill=None, fill_opacity=None, stroke=None,
       stroke_width=None, stroke_opacity=None, height=None, width=None,
       margin_left=None, margin_right=None, vertical_align=None, position=None,
       title=None, prefer_type="regular", a11y="deco") -> str:
    """Return a Font Awesome icon as an SVG string."""
    if not isinstance(name, str):
        raise ValueError("A character vector should be supplied for `name`.")
    if prefer_type not in ("regular", "solid") or a11y not in ("deco", "sem", "none"):
        raise ValueError("invalid choice")
    row = _ICONS[_index(name, prefer_type)]
    icon_width, label, path = row["width"], row["label"], row["path"]
    hnum, wnum = _length(height), _length(width)
    attrs = ""
    if height is not None and width is not None:
        attrs += 'preserveAspectRatio="none" '
    if height is None and width is None:
        height, width = "1em", f"{_r_round(icon_width / 512)}em"
    elif height is not None and width is None:
        assert hnum
        width = f"{_r_round((icon_width / 512) * hnum[0])}{hnum[1]}"
    elif height is None and width is not None:
        assert wnum
        height = f"{_r_round(wnum[0] / (icon_width / 512))}{wnum[1]}"
    if a11y == "deco":
        attrs += 'aria-hidden="true" role="img" '
    elif a11y == "sem":
        title = label if title is None else title
        attrs += f'aria-label="{html.escape(str(title), quote=True)}" role="img" '
    style = (
        f"height:{height};width:{width};vertical-align:{vertical_align or '-0.125em'};"
        f"margin-left:{margin_left or 'auto'};margin-right:{margin_right or 'auto'};"
        f"font-size:inherit;fill:{fill or 'currentColor'};overflow:visible;"
    )
    if fill_opacity is not None: style += f"fill-opacity:{fill_opacity};"
    if stroke is not None: style += f"stroke:{stroke};"
    if stroke_width is not None: style += f"stroke-width:{stroke_width};"
    if stroke_opacity is not None: style += f"stroke-opacity:{stroke_opacity};"
    style += f"position:{position or 'relative'};"
    attrs += f'viewBox="0 0 {icon_width} 512" style="{style}"'
    text = "" if title is None else f"<title>{html.escape(str(title), quote=False)}</title>"
    return f'<svg {attrs}>{text}<path d="{path}"/></svg>'
