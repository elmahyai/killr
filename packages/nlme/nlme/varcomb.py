"""Combination of variance function structures (nlme varComb)."""

from __future__ import annotations

from dataclasses import dataclass


class VarFunc:
    """Marker base for nlme variance-function stand-ins."""


def _is_var_func(obj: object) -> bool:
    if isinstance(obj, VarFunc):
        return True
    classes = getattr(obj, "classes", None)
    if classes is not None and "varFunc" in classes:
        return True
    return False


@dataclass(slots=True)
class VarComb(VarFunc):
    """Product of variance functions, inheriting from ``varFunc``."""

    components: list[VarFunc]
    names: list[str]

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varComb", "varFunc")

    def __len__(self) -> int:
        return len(self.components)

    def __getitem__(self, key: int | str) -> VarFunc:
        if isinstance(key, int):
            return self.components[key]
        if isinstance(key, str):
            try:
                index = self.names.index(key)
            except ValueError as exc:
                raise KeyError(key) from exc
            return self.components[index]
        raise TypeError(f"indices must be integers or strings, not {type(key)!r}")


def varComb(*components: VarFunc, **named: VarFunc) -> VarComb:
    """Construct a ``varComb`` object from ``varFunc`` components."""
    if named:
        if components:
            raise TypeError("varComb() accepts either positional varFunc objects or named components, not both")
        vals = list(named.values())
        names = list(named.keys())
    else:
        vals = list(components)
        names = [chr(ord("A") + index) for index in range(len(vals))]

    if vals and not all(_is_var_func(item) for item in vals):
        raise ValueError('all arguments to \'varComb\' must be of class "varFunc".')

    return VarComb(vals, names)
