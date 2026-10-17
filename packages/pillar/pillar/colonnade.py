"""Fit pillars into the width of a table body.

``colonnade()``, ``squeeze()``, and ``extra_cols()`` are defunct and stop
before any of that work. ``ctl_colonnade()`` is the live layout used by
``tbl_format_setup()``.
"""

from __future__ import annotations

from typing import Any

from lifecycle import LifecycleError

from pillar._layout import (
    defunct_message,
    distribute_pillars_rev,
    get_tier_widths,
    tick_if_needed,
    width_print,
)
from pillar._vec import DataFrame
from pillar.column import (
    PillarList,
    ctl_new_pillar,
    ctl_new_pillar_list,
    ctl_new_rowid_pillar,
    pillar_format_parts_2,
    pillar_get_min_width,
)


def colonnade(*_args: Any, **_kwargs: Any) -> None:
    """Defunct. Use ``tbl_format_setup()``."""

    raise LifecycleError(
        defunct_message("1.9.0", "pillar::colonnade()", "pillar::tbl_format_setup()")
    )


def squeeze(*_args: Any, **_kwargs: Any) -> None:
    """Defunct since pillar 1.5.0."""

    raise LifecycleError(defunct_message("1.5.0", "pillar::squeeze()"))


def extra_cols(*_args: Any, **_kwargs: Any) -> None:
    """Defunct since pillar 1.5.0."""

    raise LifecycleError(defunct_message("1.5.0", "pillar::extra_cols()"))


def _paste_columns(columns: list[list[str]]) -> list[str]:
    if not columns:
        return []
    height = max(len(column) for column in columns)
    lines: list[str] = []
    for row in range(height):
        parts = [column[row] if row < len(column) else "" for column in columns]
        lines.append(" ".join(parts))
    return lines


def _compute_used_width(tier_widths: list[int], width: int) -> dict[str, int]:
    if width <= max(tier_widths):
        used_tier = next(index + 1 for index, item in enumerate(tier_widths) if width <= item)
    else:
        used_tier = tier_widths.index(max(tier_widths)) + 1
        width = tier_widths[used_tier - 1]
    return {"tiers": used_tier - 1, "width": width}


def _compute_sub_tier_widths(
    tier_widths: list[int],
    x_pos: int,
    tier_pos: int,
    x_target: int,
    tier_target: int,
) -> list[int]:
    if tier_pos == tier_target:
        sub = [x_target - x_pos]
    else:
        sub = [tier_widths[tier_pos - 1] - x_pos]
        for tier in range(tier_pos + 1, tier_target):
            sub.append(tier_widths[tier - 1])
        sub.append(x_target)
    if x_pos > 0:
        sub[0] = max(sub[0] - 1, 0)
    return sub


def _advance_pos(x_pos: int, tier_pos: int, used: dict[str, int] | None) -> tuple[int, int]:
    if used is not None:
        if used["tiers"] > 0:
            x_pos = used["width"]
            tier_pos = tier_pos + used["tiers"]
        else:
            if x_pos > 0:
                x_pos += 1
            x_pos = x_pos + used["width"]
    return x_pos, tier_pos


class _Callbacks:
    def __init__(self, **kwargs: Any):
        self.__dict__.update(kwargs)


def _emit_extra(extra: Any, x: Any, title: Any, cb: _Callbacks) -> None:
    if extra is None or extra == [] or extra == ():
        return
    if isinstance(extra, list) and len(extra) == 0:
        return
    names = tick_if_needed(list(extra))
    if isinstance(x, DataFrame):
        shown = {}
        for name, label in zip(extra, names):
            parent = [] if title is None else ([title] if isinstance(title, str) else list(title))
            from pillar._layout import prepare_title

            key = prepare_title(parent + [label])
            shown[key] = x.columns[name]
        cb.on_extra_cols(shown)
        return
    cb.on_extra_cols({str(item): item for item in extra})


def _do_emit_pillars(
    x: Any,
    tier_widths: list[int],
    cb: _Callbacks,
    title: Any = None,
    first_pillar: Any = None,
    is_focus: bool = False,
) -> dict[str, int] | None:
    pillar_list = ctl_new_pillar_list(
        cb.controller,
        x,
        width=tier_widths,
        title=title,
        first_pillar=first_pillar,
    )
    extra = getattr(pillar_list, "extra", None)
    if len(pillar_list) == 0:
        _emit_extra(extra, x, title, cb)
        return None
    if isinstance(pillar_list, PillarList) and pillar_list.simple:
        pillar = pillar_list[0]
        title_component = pillar.components.get("title")
        title_width = 0
        if title_component is not None and getattr(title_component, "width", None) is not None:
            title_width = int(title_component.width)
        formatted = pillar_format_parts_2(
            pillar,
            max(tier_widths),
            is_focus,
            cb.on_get_n_abbrev() + 1,
        )
        true_width = int(formatted["max_extent"])
        used = _compute_used_width(tier_widths, true_width)
        if used["tiers"] > 0:
            cb.on_end_tier()
            cb.on_start_tier()
        cb.on_pillar(formatted)
        if true_width < title_width:
            inner = title_component.x[0] if hasattr(title_component, "x") else title_component
            rendered = inner.format() if hasattr(inner, "format") else str(inner)
            cb.on_abbrev(rendered)
        return used

    min_widths = [pillar_get_min_width(item) for item in pillar_list]
    rev = distribute_pillars_rev(min_widths, tier_widths)
    x_pos = 0
    tier_pos = 1
    columns = list(x.columns.items()) if isinstance(x, DataFrame) else []
    for index, pillar in enumerate(pillar_list):
        sub = _compute_sub_tier_widths(
            tier_widths,
            x_pos,
            tier_pos,
            int(rev["offset_after"][index]),
            int(rev["tier"][index]),
        )
        child = columns[index][1] if columns else x
        child_title = None
        if isinstance(x, DataFrame):
            child_title = tick_if_needed(columns[index][0])
        used = _do_emit_pillars(
            child,
            sub,
            cb,
            title=child_title,
            first_pillar=pillar,
            is_focus=is_focus,
        )
        x_pos, tier_pos = _advance_pos(x_pos, tier_pos, used)
        if first_pillar is None:
            cb.on_top_level()
    _emit_extra(extra, x, title, cb)
    return {"tiers": tier_pos - 1, "width": x_pos}


def ctl_colonnade(
    x: Any,
    has_row_id: Any = True,
    width: Any = None,
    controller: Any = None,
    focus: Any = None,
) -> dict[str, Any]:
    """Lay out ``x`` and return the body lines plus the columns that did not fit."""

    if not isinstance(x, DataFrame):
        if isinstance(x, dict):
            x = DataFrame(x)
        else:
            raise TypeError("ctl_colonnade() expects a data frame")
    if controller is None:
        controller = x
    width = width_print(width)
    focus_names = [] if focus is None else list(focus)
    unknown = [name for name in focus_names if name not in x.columns]
    if unknown:
        raise ValueError("focus columns must exist")
    if x.nrow == 0 or x.ncol == 0:
        return {"body": [], "extra_cols": {}, "abbrev_cols": [], "abbrev_col_idxs": []}
    if has_row_id is False:
        rowid = None
    else:
        rowid = ctl_new_rowid_pillar(
            controller,
            x,
            width,
            title=None,
            type=None if has_row_id is True else has_row_id,
        )
    rowid_width = 0 if rowid is None else int(rowid.width or 0)
    tier_widths = get_tier_widths(int(width), x.ncol, rowid_width + 1)
    tiers: list[list[str]] = []
    extra: dict[str, Any] = {}
    abbrev: list[Any] = []
    state: dict[str, Any] = {"formatted": []}

    def on_start_tier() -> None:
        state["formatted"] = []

    def on_end_tier() -> None:
        formatted = state["formatted"]
        if formatted:
            if rowid is not None:
                formatted = [pillar_format_parts_2(rowid, rowid_width), *formatted]
            tiers.append(_paste_columns([item["aligned"] for item in formatted]))
        state["formatted"] = []

    def on_pillar(formatted: dict[str, Any]) -> None:
        state["formatted"].append(formatted)

    def on_extra_cols(shown: dict[str, Any]) -> None:
        extra.update(shown)

    def on_abbrev(title: Any) -> None:
        abbrev.append(title)

    def on_get_n_abbrev() -> int:
        return len(abbrev)

    cb = _Callbacks(
        controller=controller,
        on_start_tier=on_start_tier,
        on_end_tier=on_end_tier,
        on_pillar=on_pillar,
        on_top_level=lambda: None,
        on_extra_cols=on_extra_cols,
        on_abbrev=on_abbrev,
        on_get_n_abbrev=on_get_n_abbrev,
    )
    on_start_tier()
    if focus_names:
        _emit_focus(x, tier_widths, cb, focus_names)
    else:
        _do_emit_pillars(x, tier_widths, cb)
    on_end_tier()
    body: list[str] = []
    for tier in tiers:
        body.extend(tier)
    return {
        "body": body,
        "extra_cols": extra,
        "abbrev_cols": abbrev,
        "abbrev_col_idxs": [],
    }


def _fits(used: int, widths: list[int], tier: int) -> bool:
    if not widths:
        return used <= tier
    gaps = len(widths) if used else len(widths) - 1
    return used + sum(widths) + gaps <= tier


def _take_focus(names: list[str], mins: list[int], focus: set[str], tier: int) -> list[str]:
    """Keep focus columns, and any earlier column that still leaves them room."""

    selected: list[str] = []
    used = 0
    for index, name in enumerate(names):
        later = [mins[later_index] for later_index in range(index + 1, len(names)) if names[later_index] in focus]
        cost = mins[index] if used == 0 else mins[index] + 1
        reserve = later
        if name in focus or _fits(used + cost, reserve, tier):
            if name in focus and not _fits(used, [mins[index]], tier):
                continue
            if name not in focus and not _fits(used + cost, reserve, tier):
                continue
            selected.append(name)
            used += cost
    return selected


def _emit_focus(x: DataFrame, tier_widths: list[int], cb: _Callbacks, focus: list[str]) -> None:
    """Show focused columns in place, dropping earlier columns that would crowd them out."""

    names = list(x.columns)
    mins: list[int] = []
    for name in names:
        pillar = ctl_new_pillar(cb.controller, x.columns[name], None, title=tick_if_needed(name))
        mins.append(pillar_get_min_width(pillar) if pillar is not None else 0)
    wanted = set(focus)
    pending = list(names)
    pending_mins = list(mins)
    chosen: list[str] = []
    for tier_index, tier in enumerate(tier_widths):
        picked = _take_focus(pending, pending_mins, wanted, int(tier))
        if tier_index > 0 and picked:
            cb.on_end_tier()
            cb.on_start_tier()
        for name in picked:
            _do_emit_pillars(
                x.columns[name],
                [int(tier)],
                cb,
                title=tick_if_needed(name),
                is_focus=name in wanted,
            )
        chosen.extend(picked)
        keep = [index for index, name in enumerate(pending) if name not in picked]
        pending = [pending[index] for index in keep]
        pending_mins = [pending_mins[index] for index in keep]
    if pending:
        cb.on_extra_cols({name: x.columns[name] for name in pending})
