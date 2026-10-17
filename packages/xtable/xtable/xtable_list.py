"""xtableList from xtable 1.8-8."""

from __future__ import annotations

from xtable.caption_replacement import Xtable
from xtable.xtable_main import RDataFrame, _is_matrix, xtable


class RList:
    """R ``list`` with optional ``subheadings`` and ``message`` attributes."""

    __slots__ = ("items", "subheadings", "message")

    def __init__(
        self,
        items: list[object],
        *,
        subheadings: list[object] | None = None,
        message: list[object] | None = None,
    ) -> None:
        self.items = items
        self.subheadings = subheadings
        self.message = message

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> object:
        return self.items[index - 1]


class XtableList:
    """List of ``xtable`` objects with shared list-level attributes."""

    __slots__ = ("items", "attrs", "classes")

    def __init__(
        self,
        items: list[Xtable],
        *,
        attrs: dict[str, object] | None = None,
        classes: tuple[str, ...] = ("xtableList",),
    ) -> None:
        self.items = items
        self.attrs = {} if attrs is None else dict(attrs)
        self.classes = classes

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> Xtable:
        return self.items[index - 1]


def _replicate_attr(n: int, value: object) -> list[object]:
    if value is None:
        return [None] * n
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            if len(value) == n:
                return list(value)
        if all(isinstance(item, str) for item in value):
            return [value] * n
    return [value] * n


def xtable_list(
    x: RList | list[object],
    *,
    caption=None,
    label=None,
    align=None,
    digits=None,
    display=None,
    **_kwargs: object,
) -> XtableList:
    if isinstance(x, RList):
        elements = x.items
        subheadings = x.subheadings
        message = x.message
    else:
        elements = x
        subheadings = None
        message = None

    n = len(elements)
    digits_list = _replicate_attr(n, digits)
    display_list = _replicate_attr(n, display)
    items: list[Xtable] = []
    for i in range(n):
        element = elements[i]
        if _is_matrix(element):
            xt = xtable(element, caption=caption, label=label, align=align, digits=digits_list[i], display=display_list[i], **_kwargs)
        elif isinstance(element, RDataFrame):
            xt = xtable(element, caption=caption, label=label, align=align, digits=digits_list[i], display=display_list[i], **_kwargs)
        else:
            xt = xtable(element, caption=caption, label=label, align=align, digits=digits_list[i], display=display_list[i], **_kwargs)
        if subheadings is not None:
            xt.attrs["subheading"] = subheadings[i]
        items.append(xt)

    attrs: dict[str, object] = {"caption": caption, "label": label}
    if message is not None:
        attrs["message"] = list(message)
    return XtableList(items, attrs=attrs)
