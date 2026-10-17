"""Minimal ``formatC`` for ``print.xtable``."""

from __future__ import annotations

import math


def format_c(
    value: float,
    *,
    format: str = "g",
    digits: int = 7,
    decimal_mark: str = ".",
) -> str:
    if value != value:
        return "NA"
    if format == "d":
        return str(int(round(value)))
    if format == "f":
        text = f"{float(value):.{int(digits)}f}"
        if decimal_mark != ".":
            text = text.replace(".", decimal_mark)
        return text
    if format in ("e", "E"):
        text = f"{float(value):.{int(digits)}e}"
        if format == "E":
            text = text.replace("e", "E")
        if decimal_mark != ".":
            text = text.replace(".", decimal_mark)
        return text
    if format in ("g", "G"):
        text = format(float(value), f".{int(digits)}g")
        if format == "G":
            text = text.replace("e", "E")
        if decimal_mark != ".":
            text = text.replace(".", decimal_mark)
        return text
    raise ValueError(f"unsupported formatC format {format!r}")


def format_c_vector(
    values: list[object],
    *,
    format: str,
    digits: int,
    decimal_mark: str = ".",
) -> list[str]:
    out: list[str] = []
    for item in values:
        if item is None or (isinstance(item, float) and item != item):
            out.append("")
            continue
        out.append(
            format_c(float(item), format=format, digits=digits, decimal_mark=decimal_mark)
        )
    return out
