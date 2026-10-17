"""Convert object to a box."""

from __future__ import annotations

from typing import Any, Sequence

from rlang import RLangError, abort, is_empty


class Box:
    """Scalar list wrapper with R-style class prefix."""

    __slots__ = ("_payload", "_classes")

    def __init__(self, payload: Any, class_: str | Sequence[str] | None = None):
        self._payload = payload
        if class_ is None:
            self._classes = ("rlang_box",)
        elif isinstance(class_, str):
            self._classes = (class_, "rlang_box")
        else:
            self._classes = tuple(class_) + ("rlang_box",)

    def __getitem__(self, index: int):
        if index != 0:
            raise IndexError("box holds a single value")
        return self._payload


def _inherits_all(x: Any, classes: Sequence[str]) -> bool:
    if is_empty(classes):
        abort("`class` can't be empty.")
    if not isinstance(x, Box):
        return False
    cls = x._classes
    need = tuple(classes)
    if len(cls) < len(need):
        return False
    return cls[: len(need)] == need


def _box_classes(class_: str | Sequence[str] | None) -> tuple[str, ...]:
    if class_ is None:
        return ("rlang_box",)
    if isinstance(class_, str):
        return (class_, "rlang_box")
    return tuple(class_) + ("rlang_box",)


def is_box(x: Any, class_: str | Sequence[str] | None = None) -> bool:
    return _inherits_all(x, _box_classes(class_))


def new_box(x: Any, class_: str | Sequence[str] | None = None, **_: Any) -> Box:
    return Box(x, class_=class_)


def unbox(box: Any) -> Any:
    if not isinstance(box, Box):
        abort("`box` must be a box")
    return box._payload


def as_box(x: Any, class_: str | Sequence[str] | None = None) -> Box:
    if is_box(x, class_):
        return x
    return new_box(x, class_=class_)
