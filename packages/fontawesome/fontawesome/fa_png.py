"""Render Font Awesome icons to PNG files."""

from __future__ import annotations

from pathlib import Path

import cairosvg

from .fa import _ICONS, fa


def fa_png(
    name: str,
    file: str | Path | None = None,
    fill=None,
    fill_opacity=None,
    stroke=None,
    stroke_width=None,
    stroke_opacity=None,
    height: int | None = None,
    width: int | None = None,
    prefer_type: str = "regular",
) -> None:
    """Write a Font Awesome icon as a PNG file."""
    svg = fa(
        name=name,
        fill=fill,
        fill_opacity=fill_opacity,
        stroke=stroke,
        stroke_width=stroke_width,
        stroke_opacity=stroke_opacity,
        prefer_type=prefer_type,
    )

    if file is None:
        if name in {row["full_name"] for row in _ICONS}:
            short_name = next(row["name"] for row in _ICONS if row["full_name"] == name)
        elif name in {row["name"] for row in _ICONS}:
            short_name = name
        else:
            # fa() has already raised for an unknown name; this is defensive.
            raise ValueError(f"The `name` provided ('{name}') does not correspond to a known icon")
        file = f"{short_name}.png"

    kwargs = {}
    if width is not None:
        kwargs["output_width"] = width
    if height is not None:
        kwargs["output_height"] = height
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(file), **kwargs)
