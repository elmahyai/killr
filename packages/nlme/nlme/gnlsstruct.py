"""Model structure for ``gnls`` fits (nlme ``gnlsStruct``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["GnlsStruct", "gnlsStruct"]


@dataclass(slots=True)
class GnlsStruct:
    """``gnlsStruct`` object holding the non-NULL correlation and variance components."""

    components: dict[str, Any] = field(default_factory=dict)
    classes: tuple[str, ...] = ("gnlsStruct", "glsStruct", "modelStruct")

    @property
    def corStruct(self) -> Any | None:
        return self.components.get("corStruct")

    @property
    def varStruct(self) -> Any | None:
        return self.components.get("varStruct")

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.components)

    def __len__(self) -> int:
        return len(self.components)

    def __getitem__(self, name: str) -> Any:
        return self.components[name]


def gnlsStruct(corStruct: Any | None = None, varStruct: Any | None = None) -> GnlsStruct:
    """Constructor for ``gnlsStruct`` objects; NULL components are dropped."""
    parts = {}
    if corStruct is not None:
        parts["corStruct"] = corStruct
    if varStruct is not None:
        parts["varStruct"] = varStruct
    return GnlsStruct(parts)
