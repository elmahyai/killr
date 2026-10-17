"""Test whether an object is an R formula or unevaluated ``~`` call."""

from __future__ import annotations

from typing import Any, Sequence

from rlang import Env


class Lang:
    """R language object (LANGSXP), usually a call."""

    __slots__ = ("op", "args", "env", "classes")

    def __init__(
        self,
        op: str,
        *args: Any,
        env: Env | None = None,
        classes: Sequence[str] = (),
    ):
        self.op = op
        self.args = args
        self.env = env
        self.classes = tuple(classes)

    def __len__(self) -> int:
        return 1 + len(self.args)


def _is_environment(value: object) -> bool:
    return isinstance(value, Env)


def _inherits_formula(x: Lang) -> bool:
    return "formula" in x.classes


def is_formula(x: object, scoped: bool | None = None, lhs: bool | None = None) -> bool:
    if not isinstance(x, Lang):
        return False
    if x.op != "~":
        return False

    if scoped is not None:
        has_env = _is_environment(x.env)
        has_class = _inherits_formula(x)
        if scoped != (has_env and has_class):
            return False

    if lhs is not None:
        has_lhs = len(x) > 2
        if lhs != has_lhs:
            return False

    return True
