"""Shared helpers for nlme correlation structures (Dim, Initialize base)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
from nlme.varconstpower import _get_groups_formula


@dataclass(frozen=True, slots=True)
class CorDim:
    """Group layout metadata matching R ``Dim.corStruct``."""

    N: int
    M: int
    max_len: int
    sum_len_sq: int
    len: tuple[int, ...]
    start: tuple[int, ...]

    def as_pdims(self) -> np.ndarray:
        parts: list[int] = [self.N, self.M, self.max_len, self.sum_len_sq]
        parts.extend(self.len)
        parts.extend(self.start)
        return np.asarray(parts, dtype=np.int32)


@dataclass(slots=True)
class _NlmeFrame:
    columns: dict[str, np.ndarray | list[Any]]

    def nrow(self) -> int:
        first = next(iter(self.columns.values()))
        return len(first)


def _as_frame(data: _NlmeFrame | Mapping[str, Any]) -> _NlmeFrame:
    if isinstance(data, _NlmeFrame):
        return data
    return _NlmeFrame({key: np.asarray(val) for key, val in data.items()})


def _normalize_formula(form: str) -> str:
    text = str(form).strip()
    if not text.startswith("~"):
        text = f"~ {text}"
    return text


def _get_groups(frame: _NlmeFrame, form: str) -> np.ndarray:
    grp_form = _get_groups_formula(form)
    if grp_form is None:
        return np.ones(frame.nrow(), dtype=np.int64)
    name = _group_var_name(grp_form)
    groups = np.asarray(frame.columns[name], dtype=np.dtype("O"))
    _, indexed = np.unique(groups, return_inverse=True)
    return indexed.astype(np.int64, copy=False)


def _group_var_name(grp_form: str) -> str:
    text = grp_form.strip()
    if text.startswith("~"):
        text = text[1:].strip()
    return text.split()[0]


def _unique_group_labels(frame: _NlmeFrame, form: str) -> list[Any]:
    grp_form = _get_groups_formula(form)
    if grp_form is None:
        return [1]
    name = _group_var_name(grp_form)
    groups = np.asarray(frame.columns[name], dtype=np.dtype("O"))
    # Sorted, like R factor levels, so label i matches the integer group code i from _get_groups.
    return [value.item() if hasattr(value, "item") else value for value in np.unique(groups)]


def Dim(object, groups: Sequence[int] | np.ndarray | None = None) -> CorDim:
    """Return correlation dimensions for an initialized ``corStruct`` object."""
    if groups is None:
        stored = getattr(object, "dim", None)
        if stored is None:
            raise ValueError("corStruct object has no Dim attribute")
        return stored
    grp = np.asarray(groups, dtype=np.int64).reshape(-1)
    ugrp, indexed = np.unique(grp, return_inverse=True)
    counts = np.bincount(indexed)
    sum_len_sq = int(np.sum(counts.astype(np.int64) ** 2))
    if sum_len_sq > np.iinfo(np.int32).max:
        raise ValueError(
            f"'sumLenSq := sum(table(groups)^2)' = {sum_len_sq} is too large."
        )
    start = np.zeros(len(counts), dtype=np.int64)
    if len(counts) > 1:
        start[1:] = np.cumsum(counts[:-1])
    return CorDim(
        N=int(grp.size),
        M=int(len(counts)),
        max_len=int(np.max(counts)),
        sum_len_sq=sum_len_sq,
        len=tuple(int(x) for x in counts),
        start=tuple(int(x) for x in start),
    )


def _default_covariate(frame: _NlmeFrame, form: str) -> Any:
    cov_form = getCovariateFormula(form).text
    cov_vars = _all_vars(cov_form)
    grp_form = _get_groups_formula(form)
    if cov_vars:
        # R getCovariate.corStruct: the covariate column, split by group when the formula has groups.
        if len(cov_vars) != 1:
            raise NotImplementedError("corStruct covariates with more than one variable are not implemented")
        values = np.asarray(frame.columns[cov_vars[0]])
        if grp_form is None:
            return values
        group_labels = _unique_group_labels(frame, form)
        group_values = np.asarray(frame.columns[_group_var_name(grp_form)], dtype=np.dtype("O"))
        return {label: values[group_values == label] for label in group_labels}
    if grp_form is None:
        return np.arange(1, frame.nrow() + 1, dtype=np.int64)
    labels = _unique_group_labels(frame, form)
    name = _group_var_name(grp_form)
    groups = np.asarray(frame.columns[name], dtype=np.dtype("O"))
    out: dict[Any, np.ndarray] = {}
    for label in labels:
        mask = groups == label
        out[label] = np.arange(1, int(np.sum(mask)) + 1, dtype=np.int64)
    return out


def initialize_cor_struct(object, data: _NlmeFrame | Mapping[str, Any]):
    """Apply ``Initialize.corStruct`` grouping and covariate setup."""
    frame = _as_frame(data)
    form = _normalize_formula(object.formula)
    groups = _get_groups(frame, form)
    labels = _unique_group_labels(frame, form)
    object.groups = np.asarray([labels[int(g)] for g in groups], dtype=np.dtype("O"))
    object.dim = Dim(object, groups)
    object.covariate = _default_covariate(frame, form)
    object.formula = form
    return object
