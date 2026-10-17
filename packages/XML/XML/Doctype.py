"""Doctype constructor and DOCTYPE string rendering."""

from __future__ import annotations

from typing import Sequence


def _as_str_vector(value: str | Sequence[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value]


def _validate_public_identifier(identifier: str) -> str | None:
    parts = identifier.split("//")
    if len(parts) != 4:
        return "a PUBLIC identifier must have 4 parts, separated by //"
    if parts[0] not in ("+", "-"):
        return "first element of PUBLIC identifier must be + or -"
    return None


def _dd_quote(values: Sequence[str]) -> list[str]:
    if not values:
        return []
    return [f'"{value}"' for value in values]


class _Doctype:
    """Reference to an XML DTD for the document DOCTYPE declaration."""

    __slots__ = ("name", "system", "public")

    def __init__(self, name: str = "", system: Sequence[str] | str | None = None, public: Sequence[str] | str | None = None) -> None:
        self.name = str(name)
        self.system = _as_str_vector(system)
        self.public = _as_str_vector(public)
        message = _validate_doctype(self)
        if message is not True:
            raise ValueError(message)

    def __str__(self) -> str:
        return _doctype_as_character(self)


def _validate_doctype(obj: _Doctype) -> str | bool:
    if len(obj.system) > 0 and len(obj.public) > 0:
        return "only one of system and public can be specified"
    if len(obj.public) > 0 and len(obj.public) != 2:
        return "the public part of the Doctype must have exactly 2 elements."
    if len(obj.public) > 0:
        message = _validate_public_identifier(obj.public[0])
        if message is not None:
            return message
    return True


def Doctype(system: str | Sequence[str] | None = None, public: str | Sequence[str] | None = None, name: str = "") -> _Doctype:
    """Build a Doctype object naming the root element and a SYSTEM or PUBLIC DTD reference."""
    system_vec = _as_str_vector(system)
    public_vec = _as_str_vector(public)
    if len(public_vec) == 1 and len(system_vec) > 0:
        public_vec = [public_vec[0], system_vec[0]]
        system_vec = []
    return _Doctype(name=name, system=system_vec, public=public_vec)


def _doctype_as_character(from_obj: _Doctype) -> str:
    extra: list[str] = []
    if sum(len(part) for part in from_obj.public) + sum(len(part) for part in from_obj.system):
        if from_obj.system:
            extra.extend(["SYSTEM", *_dd_quote(from_obj.system)])
        if from_obj.public:
            extra.extend(["PUBLIC", *_dd_quote(from_obj.public)])
    middle = " ".join(extra)
    return " ".join(["<!DOCTYPE", from_obj.name, middle, ">"])


def as_character(doctype: _Doctype) -> str:
    """R's as(d, \"character\") for a Doctype object."""
    return _doctype_as_character(doctype)
