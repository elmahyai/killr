"""xtableLSMeans from xtable 1.8-8."""

from __future__ import annotations

from xtable.xtable_main import Factor, RDataFrame, xtable_data_frame
from xtable.xtable_list import RList, xtable_list


class LSMeansFrame:
    """Data frame with ``estName`` and ``mesg`` attributes."""

    __slots__ = ("columns", "row_names", "est_name", "mesg", "col_names")

    def __init__(
        self,
        columns: dict[str, list[object]],
        *,
        est_name: str = "lsmean",
        mesg: list[str] | str | None = None,
        col_names: list[str] | None = None,
        row_names: list[object] | None = None,
    ) -> None:
        self.columns = columns
        self.row_names = row_names
        self.est_name = est_name
        if mesg is None:
            self.mesg: list[str] = []
        elif isinstance(mesg, str):
            self.mesg = [mesg]
        else:
            self.mesg = list(mesg)
        self.col_names = col_names if col_names is not None else list(columns.keys())


def _factor_levels(values: list[object]) -> list[object]:
    levels: list[object] = []
    seen: set[object] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            levels.append(value)
    return levels


def xtable_lsmeans(
    x: LSMeansFrame | RDataFrame,
    *,
    caption=None,
    label=None,
    align=None,
    digits=None,
    display=None,
    auto: bool = False,
    **_kwargs: object,
) -> object:
    est_name = getattr(x, "est_name", None)
    if est_name == "lsmean":
        col_names = x.col_names if hasattr(x, "col_names") else list(x.columns.keys())
        split_col = col_names[1]
        factor_col = x.columns[split_col]
        values = factor_col.values if isinstance(factor_col, Factor) else list(factor_col)
        levels = (
            list(factor_col.levels)
            if isinstance(factor_col, Factor) and factor_col.levels
            else _factor_levels(values)
        )

        pieces: list[RDataFrame] = []
        subheadings: list[str] = []
        for level in levels:
            keep: dict[str, list[object]] = {}
            keep_idx = [i for i, v in enumerate(values) if v == level]
            for name in col_names:
                if name == split_col:
                    continue
                col = x.columns[name]
                col_vals = col.values if isinstance(col, Factor) else col
                keep[name] = [col_vals[i] for i in keep_idx]
            pieces.append(
                RDataFrame(keep, row_names=[str(i + 1) for i in range(len(keep_idx))])
            )
            subheadings.append(f"{split_col} = {level}")

        mesg = getattr(x, "mesg", [])
        message = ["", *mesg] if mesg else [""]
        return xtable_list(
            RList(pieces, subheadings=subheadings, message=message),
            caption=caption,
            label=label,
            align=align,
            digits=digits,
            display=display,
            auto=auto,
            **_kwargs,
        )

    frame = x if isinstance(x, RDataFrame) else RDataFrame(x.columns, row_names=x.row_names)
    return xtable_data_frame(
        frame,
        caption=caption,
        label=label,
        align=align,
        digits=digits,
        display=display,
        auto=auto,
    )
