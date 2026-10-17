"""Model structure for ``gls`` fits (nlme ``glsStruct``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["GlsStruct", "glsStruct"]


@dataclass(slots=True)
class GlsStruct:
    """``glsStruct`` / ``modelStruct`` holding the non-NULL components in order."""

    components: dict[str, Any] = field(default_factory=dict)
    classes: tuple[str, ...] = ("glsStruct", "modelStruct")
    # R attributes set by Initialize.glsStruct and gls: the parameter map (rows are
    # coefficients, columns are components) and the fixed-sigma flag.
    pmap: Any = None
    fixedSigma: bool = False

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


def glsStruct(corStruct: Any | None = None, varStruct: Any | None = None) -> GlsStruct:
    """Constructor for ``glsStruct`` objects; NULL components are dropped."""
    parts = {}
    if corStruct is not None:
        parts["corStruct"] = corStruct
    if varStruct is not None:
        parts["varStruct"] = varStruct
    return GlsStruct(parts)
