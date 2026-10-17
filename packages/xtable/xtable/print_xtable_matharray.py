"""print.xtableMatharray from xtable 1.8-8."""

from __future__ import annotations

from typing import Any

from xtable.caption_replacement import Xtable
from xtable.print_xtable import print_xtable


def print_xtable_matharray(
    x: Xtable,
    *,
    print_results: bool = True,
    format_args: dict | None = None,
    scalebox: str | None = None,
    comment: bool = True,
    timestamp: str | None = None,
    **kwargs: Any,
) -> str:
    x.classes = ("xtableMatharray", "data.frame")
    return print_xtable(
        x,
        floating=False,
        tabular_environment="array",
        include_rownames=False,
        include_colnames=False,
        hline_after=[],
        print_results=print_results,
        format_args=format_args,
        comment=comment,
        timestamp=timestamp,
        **kwargs,
    )
