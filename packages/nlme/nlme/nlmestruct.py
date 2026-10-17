"""Model structure for nlme fits (nlme ``nlmeStruct``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["NlmeStruct", "nlmeStruct"]


@dataclass(slots=True)
class NlmeStruct:
    """Ordered list of non-NULL model components with the ``settings`` attribute.

    ``components`` keeps the R list names ``reStruct``, ``corStruct``, and
    ``varStruct`` in that order, without the NULL entries.
    """

    components: dict[str, Any] = field(default_factory=dict)
    settings: Any = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("nlmeStruct", "lmeStruct", "modelStruct")

    def __len__(self) -> int:
        return len(self.components)

    def __iter__(self):
        return iter(self.components.values())

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, str):
            return self.components[key]
        return list(self.components.values())[key]

    @property
    def names(self) -> list[str]:
        return list(self.components.keys())


def nlmeStruct(reStruct: Any, corStruct: Any = None, varStruct: Any = None) -> NlmeStruct:
    """Build an ``nlmeStruct`` from a random-effects, correlation, and variance structure.

    NULL components are dropped. The ``settings`` attribute is taken from the
    random-effects structure, as in the R constructor.
    """
    values = {"reStruct": reStruct, "corStruct": corStruct, "varStruct": varStruct}
    kept = {name: value for name, value in values.items() if value is not None}
    settings = getattr(reStruct, "settings", None) if reStruct is not None else None
    return NlmeStruct(components=kept, settings=settings)
