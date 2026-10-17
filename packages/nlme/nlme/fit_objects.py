"""Minimal fitted-model stand-ins for ``augPred`` and ``predict``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from nlme.lmlistformula import LmList, LmFit


@dataclass(slots=True)
class LmeCall:
    data: Any


@dataclass(slots=True)
class LmeDims:
    Q: int


@dataclass(slots=True)
class LmeCoefficients:
    fixed: np.ndarray
    fixed_names: tuple[str, ...]
    random: dict[str, np.ndarray]
    random_rownames: dict[str, tuple[str, ...]]
    random_colnames: dict[str, tuple[str, ...]]


@dataclass(slots=True)
class LmeFit:
    """``lme`` object sufficient for ``augPred.lme`` / ``predict.lme`` (single level)."""

    call: LmeCall
    dims: LmeDims
    groups: dict[str, list[Any]]
    group_colnames: tuple[str, ...]
    group_level_labels: tuple[str, ...]
    coefficients: LmeCoefficients
    formula: str
    fitted_values: np.ndarray
    resid_values: np.ndarray
    labels: dict[str, str] | None = None
    units: dict[str, str] | None = None
    classes: tuple[str, ...] = ("lme",)

    def __getitem__(self, key: str):
        if key == "groups":
            return self.groups
        raise KeyError(key)


@dataclass(slots=True)
class LmListFit(LmList):
    """``lmList`` with fitted/residual vectors for ``getResponse``."""

    fitted_values: np.ndarray | None = None
    resid_values: np.ndarray | None = None
    groups_vector: list[Any] | None = None
    call: Any = None
    classes: tuple[str, ...] = ("lmList",)

    def __getitem__(self, key: str):
        if key == "data":
            if self.call is None:
                raise KeyError(key)
            return self.call.data
        return super().__getitem__(key)


def lm_list_entry_map(object: LmList) -> dict[str, LmFit]:
    out: dict[str, LmFit] = {}
    for name, entry in object.entries:
        if isinstance(entry, LmFit):
            out[name] = entry
    return out
