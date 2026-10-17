"""In-memory string accumulator used by ``print.xtable`` (R ``string`` class)."""

from __future__ import annotations


class StringConnection:
    __slots__ = ("text", "file", "append")

    def __init__(self, text: str = "", *, file: str = "", append: bool = False) -> None:
        self.text = text
        self.file = file
        self.append = append


def is_string(value: object) -> bool:
    return isinstance(value, StringConnection)


def string(
    text: str = "", *, file: str = "", append: bool = False
) -> StringConnection:
    return StringConnection(text, file=file, append=append)


def as_string(value: object, *, file: str = "", append: bool = False) -> StringConnection:
    if is_string(value):
        return value
    if isinstance(value, str):
        return string(value, file=file, append=append)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return string(str(value), file=file, append=append)
    raise ValueError("Cannot coerce argument to a string")


def add_string(left: StringConnection, right: object) -> StringConnection:
    right_str = as_string(right)
    left.text = left.text + right_str.text
    return left
