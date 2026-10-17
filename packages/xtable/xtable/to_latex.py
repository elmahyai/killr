"""toLatex.xtable from xtable 1.8-8."""

from __future__ import annotations

from typing import Any

from xtable.caption_replacement import Xtable
from xtable.print_xtable import print_xtable


def _map_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "print.results": "print_results",
        "include.rownames": "include_rownames",
        "include.colnames": "include_colnames",
        "only.contents": "only_contents",
        "NA.string": "na_string",
        "hline.after": "hline_after",
        "floating.environment": "floating_environment",
        "table.placement": "table_placement",
        "caption.placement": "caption_placement",
        "latex.environments": "latex_environments",
        "tabular.environment": "tabular_environment",
        "sanitize.text.function": "sanitize_text_function",
        "sanitize.rownames.function": "sanitize_rownames_function",
        "sanitize.colnames.function": "sanitize_colnames_function",
        "math.style.negative": "math_style_negative",
        "math.style.exponents": "math_style_exponents",
        "format.args": "format_args",
    }
    out = dict(kwargs)
    for r_key, py_key in mapping.items():
        if r_key in out:
            out[py_key] = out.pop(r_key)
    return out


def to_latex_xtable(object: Xtable, **kwargs: Any) -> list[str]:
    opts = _map_kwargs(kwargs)
    opts.setdefault("type", "latex")
    opts["print_results"] = False
    text = print_xtable(object, **opts)
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines
