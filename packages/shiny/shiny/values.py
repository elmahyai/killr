"""R values these two functions distinguish."""

from __future__ import annotations


class ShinyError(Exception):
    """An error whose message is the one R reports."""


class Missing:
    """An R missing value. Logical NA is not a number and not a string."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def __repr__(self) -> str:
        if self.mode == "logical":
            return "NA"
        if self.mode == "integer":
            return "NA_integer_"
        if self.mode == "character":
            return "NA_character_"
        if self.mode == "complex":
            return "NA_complex_"
        return "NA_real_"


NA = Missing("logical")
NA_integer_ = Missing("integer")
NA_real_ = Missing("double")
NA_complex_ = Missing("complex")
NA_character_ = Missing("character")


class Vector:
    """An atomic vector. A Python str is one string, and a list is an R list."""

    def __init__(self, data, mode: str, classes=()) -> None:
        self.data = list(data)
        self.mode = mode
        self.classes = tuple(classes)

    def __repr__(self) -> str:
        return f"Vector({self.data!r}, {self.mode!r})"


class WithClass:
    """An object whose class attribute is `classes`."""

    def __init__(self, value, classes) -> None:
        self.value = value
        self.classes = tuple(classes)

    def __repr__(self) -> str:
        return f"WithClass({self.value!r}, {self.classes!r})"


class NamedList:
    """An R list. Names may be duplicated or blank, and order is kept."""

    def __init__(self, pairs=None) -> None:
        self.pairs = list(pairs or [])

    def first(self, name: str):
        for key, value in self.pairs:
            if key == name:
                return value
        return None

    def set_first(self, name: str, value) -> None:
        for index, (key, _) in enumerate(self.pairs):
            if key == name:
                self.pairs[index] = (name, value)
                return
        self.pairs.append((name, value))

    def remove_first(self, name: str) -> None:
        for index, (key, _) in enumerate(self.pairs):
            if key == name:
                del self.pairs[index]
                return

    def __repr__(self) -> str:
        return f"NamedList({self.pairs!r})"
