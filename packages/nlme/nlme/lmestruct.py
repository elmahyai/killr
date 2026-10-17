"""Model structure for ``lme`` fits (nlme ``lmeStruct``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.restruct import ReStruct


@dataclass(slots=True)
class LmeStruct:
    """``lmeStruct`` object: non-NULL components plus the ``settings`` attribute."""

    components: dict[str, Any]
    settings: np.ndarray | None
    classes: tuple[str, ...] = ("lmeStruct", "modelStruct")

    def __len__(self) -> int:
        return len(self.components)

    @property
    def names(self) -> list[str]:
        return list(self.components)

    def __getitem__(self, key: str) -> Any:
        return self.components[key]

    @property
    def reStruct(self) -> ReStruct | None:
        return self.components.get("reStruct")

    @property
    def corStruct(self) -> Any:
        return self.components.get("corStruct")

    @property
    def varStruct(self) -> Any:
        return self.components.get("varStruct")


def lmeStruct(
    reStruct: ReStruct,
    corStruct: Any = None,
    varStruct: Any = None,
) -> LmeStruct:
    """Build an ``lmeStruct`` from random, correlation and variance structures.

    NULL components are dropped, as in R.  The ``settings`` attribute is taken
    from ``reStruct``.
    """
    candidates = {"reStruct": reStruct, "corStruct": corStruct, "varStruct": varStruct}
    components = {name: value for name, value in candidates.items() if value is not None}
    settings = getattr(reStruct, "settings", None) if reStruct is not None else None
    return LmeStruct(components=components, settings=settings)
