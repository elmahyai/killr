"""Pillars: a title, a type, and a shaft, plus the row-id column.

``pillar()`` builds the three standard components. ``new_pillar()`` keeps
whatever components it is given. A data frame, matrix, or array becomes a
list of those pillars through ``ctl_new_pillar_list()``.
"""

from __future__ import annotations

from typing import Any

from pillar._layout import lines_of, prepare_title, tick_if_needed
from pillar._text import is_na
from pillar._vec import DataFrame, Matrix, Table, vec_size
from pillar.extent import align
from pillar.parts import (
    new_pillar_component,
    new_pillar_title,
    new_pillar_type,
    pillar_component,
)
from pillar.shaft import new_empty_shaft, new_continuation_shaft, pillar_shaft, rif_shaft
from pillar._color import grey_0_8


class Pillar:
    """Named components and an optional width."""

    def __init__(self, components: dict[str, Any], width: Any, classes: list[str]):
        self.components = dict(components)
        self.width = width
        self.classes = list(classes)

    def format(self, width: Any = None, **_ignored: Any) -> list[str]:
        use = width
        if use is None:
            use = self.width
        if use is None:
            use = pillar_get_width(self)
        return pillar_format_parts_2(self, use)["aligned"]

    def __repr__(self) -> str:
        names = ", ".join(self.components)
        return f"pillar({names}; width={self.width})"


class PillarList(list):
    """Pillars for one compound column, plus the names that did not fit."""

    def __init__(self, pillars: list[Any], extra: Any, remaining_width: Any, simple: bool):
        super().__init__(pillars)
        self.extra = extra
        self.remaining_width = remaining_width
        self.simple = simple


class RifType:
    """The type row of a row-id column. A star means the data has row names."""

    def __init__(self, star: str):
        self.star = star
        self.width = 1
        self.min_width = 1

    def format(self, width: Any = None, **_ignored: Any) -> str:
        if not self.star:
            return ""
        return grey_0_8(self.star)


def _component_width(component: Any) -> Any:
    if isinstance(component, str) or component is None or is_na(component):
        return None
    return getattr(component, "width", None)


def _component_min_width(component: Any) -> Any:
    if isinstance(component, str) or component is None or is_na(component):
        return None
    if getattr(component, "min_width", None) is not None:
        return component.min_width
    return getattr(component, "width", None)


def pillar_get_width(x: Any) -> int:
    widths = [_component_width(component) for component in _components(x).values()]
    numbers = [int(item) for item in widths if isinstance(item, (int, float)) and item == item]
    if not numbers:
        return 0
    return int(max(numbers))


def pillar_get_min_width(x: Any) -> int:
    widths = [_component_min_width(component) for component in _components(x).values()]
    numbers = [int(item) for item in widths if isinstance(item, (int, float)) and item == item]
    if not numbers:
        return 0
    return int(max(numbers))


def _components(x: Any) -> dict[str, Any]:
    if isinstance(x, Pillar):
        return x.components
    if isinstance(x, dict):
        return x
    return {}


def _unwrap(component: Any) -> tuple[Any, Any]:
    if isinstance(component, str) or component is None or is_na(component):
        return component, None
    if type(component).__name__ == "PillarComponent":
        return component.x[0], component.width
    return component, getattr(component, "width", None)


def _render(inner: Any, width: Any, is_focus: bool, footnote_idx: int) -> Any:
    if isinstance(inner, str) or inner is None or is_na(inner):
        return "" if inner is None else inner
    formatter = getattr(inner, "format", None)
    if formatter is None:
        return "" if inner == "" else str(inner)
    return formatter(width=width, is_focus=is_focus, footnote_idx=footnote_idx)


def pillar_format_parts_2(
    x: Any,
    width: Any,
    is_focus: bool = False,
    footnote_idx: int = 1,
) -> dict[str, Any]:
    """Format every component, then align the lines to the widest one."""

    components = _components(x)
    flat: list[str] = []
    side = "left"
    for name, component in components.items():
        inner, stored = _unwrap(component)
        use = width if stored is None else min(int(width), int(stored))
        rendered = _render(inner, use, is_focus, footnote_idx)
        if name == "data":
            chosen = getattr(rendered, "align", None)
            if chosen:
                side = chosen
        flat.extend(lines_of(rendered))
    if not flat:
        return {"max_extent": 0, "aligned": [], "components": list(components)}
    from pillar.extent import get_extent

    extents = get_extent(flat)
    if isinstance(extents, int):
        extents = [extents]
    max_extent = max(extents) if extents else 0
    if max_extent > width:
        from pillar._layout import str_trunc

        flat = str_trunc(flat, width)
        max_extent = int(width)
    aligned = align(flat, width=max_extent, align=side)
    if isinstance(aligned, str):
        aligned = [aligned]
    return {"max_extent": max_extent, "aligned": list(aligned), "components": list(components)}


def _max0(width: Any) -> int:
    if width is None:
        return 0
    if isinstance(width, (int, float)) and not isinstance(width, bool):
        return int(width)
    if not width:
        return 0
    return int(max(width))


def pillar(x: Any, title: Any = None, width: Any = None, **kwargs: Any) -> Any:
    """A title, a type, and the shaft for ``x``. ``None`` when ``width`` is too small."""

    return pillar_from_shaft(
        new_pillar_title(title),
        new_pillar_type(x),
        pillar_shaft(x, **kwargs),
        width,
    )


def pillar_from_shaft(title: Any, type_: Any, data: Any, width: Any) -> Any:
    my_width = float("inf") if width is None else width
    if _component_min_width(title) is not None and _component_min_width(title) > my_width:
        return None
    data_min = data.min_width if data.min_width is not None else data.width
    if data_min is not None and data_min > my_width:
        return None
    shaft_type = getattr(data, "type", None)
    if shaft_type is not None:
        type_ = shaft_type
    if _component_min_width(type_) is not None and _component_min_width(type_) > my_width:
        return None
    data_component = new_pillar_component([data], width=data.width, min_width=data_min)
    return new_pillar(
        {
            "title": pillar_component(title),
            "type": pillar_component(type_),
            "data": data_component,
        },
        width=width,
    )


def new_pillar(
    components: Any,
    *args: Any,
    width: Any = None,
    class_: Any = None,
    extra: Any = None,
    **kwargs: Any,
) -> Pillar:
    """Low-level pillar. Every component needs a name."""

    if args or kwargs:
        raise TypeError("unused arguments")
    if extra is not None:
        from lifecycle import deprecate_warn

        deprecate_warn("1.7.0", "pillar::new_pillar(extra = )", package="pillar")
    if isinstance(components, Pillar):
        components = components.components
    if not isinstance(components, dict):
        raise TypeError("All components must have names.")
    if components and any(not name for name in components):
        raise ValueError("All components must have names.")
    classes = ["pillar"]
    if class_ is not None:
        if isinstance(class_, str):
            classes = [class_, "pillar"]
        else:
            classes = list(class_) + ["pillar"]
    return Pillar(components, width, classes)


def ctl_new_pillar(controller: Any, x: Any, width: Any, title: Any = None, **kwargs: Any) -> Any:
    """One pillar for an atomic column. ``width`` may be one tier or several."""

    if kwargs:
        raise TypeError("unused arguments")
    chosen = None if width is None else _max0(width)
    return pillar(x, title, chosen)


def ctl_new_rowid_pillar(
    controller: Any,
    x: Any,
    width: Any,
    title: Any = None,
    type: Any = None,
    **kwargs: Any,
) -> Any:
    """The row-number column. ``type="*"`` prints a star on the type row."""

    if kwargs:
        raise TypeError("unused arguments")
    if width is not None and not isinstance(width, (int, float)) and len(width) == 0:
        return None
    if isinstance(width, (int, float)) and width == 0:
        return None
    template = ctl_new_pillar(controller, [], width, title=title)
    if template is None or not template.components:
        return None
    data = rif_shaft(_nrow(x))
    out: dict[str, Any] = {name: "" for name in template.components}
    if "type" in out:
        out["type"] = pillar_component(RifType("*" if type == "*" else ""))
    if "data" in out:
        out["data"] = pillar_component(data)
    return new_pillar(out, width=data.width)


def _nrow(x: Any) -> int:
    if isinstance(x, (DataFrame, Matrix)):
        return x.nrow
    return vec_size(x)


def _ncol(x: Any) -> int:
    if isinstance(x, DataFrame):
        return x.ncol
    if isinstance(x, Matrix):
        return x.ncol
    return 0


def ctl_new_pillar_list(
    controller: Any,
    x: Any,
    width: Any,
    title: Any = None,
    first_pillar: Any = None,
    **kwargs: Any,
) -> PillarList:
    """Pillars for ``x``. A data frame, matrix, or array contributes one per sub-column."""

    if kwargs:
        raise TypeError("unused arguments")
    if isinstance(x, DataFrame):
        return _data_frame_pillars(x, controller, width, title, first_pillar)
    if isinstance(x, Matrix):
        return _matrix_pillars(x, controller, width, title, first_pillar)
    if isinstance(x, Table) and len(x.dim) > 2:
        return _array_pillars(x, controller, width, title, first_pillar)
    if first_pillar is None:
        first_pillar = ctl_new_pillar(controller, x, width, title=prepare_title(title))
    return _single_pillar_list(first_pillar, width)


def _single_pillar_list(pillar_obj: Any, width: Any) -> PillarList:
    if pillar_obj is None:
        return PillarList([], None, None, True)
    minimum = pillar_get_min_width(pillar_obj)
    if width is None:
        remaining = None
    else:
        remaining = deduct_width(width, minimum)
        if remaining is None:
            raise ValueError("pillar does not fit")
    return PillarList([pillar_obj], None, remaining, True)


def _as_widths(width: Any) -> list[int] | None:
    if width is None:
        return None
    if isinstance(width, bool):
        raise TypeError("width must be numeric")
    if isinstance(width, (int, float)):
        return [int(width)]
    return [int(item) for item in width]


def deduct_width(width: Any, consumed: Any) -> Any:
    """Subtract a column from the tier widths. ``None`` means it does not fit."""

    consumed_list: list[Any]
    if consumed is None:
        return width
    if isinstance(consumed, (int, float)) and not isinstance(consumed, bool):
        consumed_list = [int(consumed)]
    else:
        consumed_list = list(consumed)
    if len(consumed_list) == 0:
        return width
    widths = _as_widths(width)
    if widths is None:
        return None
    if len(widths) == 0:
        return None
    if widths[0] >= consumed_list[0]:
        nxt = [max(widths[0] - consumed_list[0] - 1, 0), *widths[1:]]
        return deduct_width(nxt, consumed_list[1:])
    return deduct_width(widths[1:], consumed_list)


def _data_frame_pillars(
    x: DataFrame,
    controller: Any,
    width: Any,
    title: Any,
    first_pillar: Any,
) -> PillarList:
    names = list(x.columns)
    if not names:
        built = pillar_from_shaft(
            new_pillar_title(prepare_title(title)),
            new_pillar_type(x),
            new_empty_shaft(x.nrow),
            None if width is None else _max0(width),
        )
        return _single_pillar_list(built, width)
    ticked = tick_if_needed(names)
    pillars: list[Any] = []
    current_title = title
    for index, name in enumerate(names):
        if index == 0 and first_pillar is not None:
            column = first_pillar
        else:
            parent = [] if current_title is None else (
                [current_title] if isinstance(current_title, str) else list(current_title)
            )
            sub = ctl_new_pillar_list(
                controller,
                x.columns[name],
                width=None,
                title=parent + [ticked[index]],
            )
            if len(sub) == 0:
                break
            column = sub[0]
        if column is None:
            break
        if width is None:
            return PillarList([column], None, None, False)
        remaining = deduct_width(width, pillar_get_min_width(column))
        if remaining is None:
            break
        pillars.append(column)
        width = remaining
        if current_title is not None:
            if isinstance(current_title, str):
                current_title = ""
            else:
                current_title = [""] * len(current_title)
    extra = names[len(pillars):]
    return PillarList(pillars, extra, width, False)


def _matrix_pillars(
    x: Matrix,
    controller: Any,
    width: Any,
    title: Any,
    first_pillar: Any,
) -> PillarList:
    if x.ncol == 0:
        built = pillar_from_shaft(
            new_pillar_title(prepare_title(title)),
            new_pillar_type(x),
            new_empty_shaft(x.nrow),
            None if width is None else _max0(width),
        )
        return _single_pillar_list(built, width)
    labels = [f"[,{index}]" for index in range(1, x.ncol + 1)]
    pillars: list[Any] = []
    for index, label in enumerate(labels):
        if index == 0 and first_pillar is not None:
            column = first_pillar
        else:
            parent: list[Any] = []
            if title is not None:
                parent = [title] if isinstance(title, str) else list(title)
                if index > 0 and parent:
                    parent[-1] = ""
            start = index * x.nrow
            values = x.data[start : start + x.nrow]
            column = ctl_new_pillar(
                controller,
                values,
                width=None,
                title=prepare_title(parent + [label]),
            )
        if column is None:
            break
        if width is None:
            return PillarList([column], None, None, False)
        remaining = deduct_width(width, pillar_get_min_width(column))
        if remaining is None:
            break
        pillars.append(column)
        width = remaining
    extra = list(range(len(pillars) + 1, x.ncol + 1))
    return PillarList(pillars, extra, width, False)


def _array_pillars(
    x: Table,
    controller: Any,
    width: Any,
    title: Any,
    first_pillar: Any,
) -> PillarList:
    if first_pillar is not None:
        return PillarList([first_pillar], None, width, True)
    size = vec_size(x)
    body = pillar_shaft([None] * size)
    built = pillar_from_shaft(
        new_pillar_title(title),
        new_pillar_type(x),
        new_continuation_shaft(body),
        None if width is None else _max0(width),
    )
    return _single_pillar_list(built, width)
