"""Extract variance-covariance matrices from fitted models (nlme ``getVarCov``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

_MISSING = object()
_VARCOV_TYPES = ("random.effects", "conditional", "marginal")


@dataclass(slots=True)
class ReStructBlock:
    """First-level ``reStruct`` block; ``as_matrix`` matches ``as.matrix(reStruct[[1]])``."""

    as_matrix: np.ndarray


@dataclass(slots=True)
class ModelStruct:
    """``modelStruct`` slice used by ``getVarCov``."""

    reStruct: tuple[ReStructBlock, ...]
    corStruct: Any | None = None
    varStruct: Any | None = None


@dataclass(slots=True)
class Lme:
    """``lme`` stand-in for ``getVarCov.lme`` (single nesting level)."""

    sigma: float
    modelStruct: ModelStruct
    groups: tuple[Sequence[Any], ...]
    group_names: tuple[str, ...] = ("Subject",)
    data: Any | None = None
    classes: tuple[str, ...] = ("lme",)


@dataclass(slots=True)
class Gls:
    """``gls`` stand-in for ``getVarCov.gls``."""

    sigma: float
    modelStruct: ModelStruct
    group_names: tuple[str, ...]
    classes: tuple[str, ...] = ("gls",)


class VarCovError(ValueError):
    """An R-style ``stop`` from ``getVarCov`` or its methods."""


@dataclass(frozen=True, slots=True)
class VarCovMatrix:
    """Matrix result with ``random.effects`` / ``marginal`` and ``VarCov`` classes."""

    values: np.ndarray
    classes: tuple[str, ...]
    group_levels: tuple[str, ...]

    def __array__(self, dtype=None, copy=None):
        if dtype is None:
            dtype = np.float64
        return np.asarray(self.values, dtype=dtype, copy=copy)


@dataclass(frozen=True, slots=True)
class VarCovList:
    """List result for ``conditional`` or ``marginal`` ``lme`` methods."""

    items: tuple[tuple[str, np.ndarray], ...]
    classes: tuple[str, ...]
    group_levels: tuple[str, ...]

    def __getitem__(self, key: str) -> np.ndarray:
        for name, matrix in self.items:
            if name == key:
                return matrix
        raise KeyError(key)


def getVarCov(
    obj,
    individuals=_MISSING,
    type=_MISSING,
    individual: Any = 1,
    **kwargs,
):
    """Extract a variance-covariance matrix or a list of matrices from a fitted model."""
    del kwargs
    classes = _class_vector(obj)
    if "lme" in classes:
        if type is _MISSING:
            type = "random.effects"
        return _get_var_cov_lme(obj, individuals, type)
    if "gls" in classes:
        return _get_var_cov_gls(obj, individual)
    shown = _show_classes(classes)
    raise TypeError(f"no applicable method for 'getVarCov' applied to an object of class {shown}")


def _get_var_cov_lme(
    obj: Lme,
    individuals: Any,
    type: str,
) -> VarCovMatrix | VarCovList:
    type = _match_arg(type, _VARCOV_TYPES)
    classes = _class_vector(obj)
    if "nlme" in classes:
        raise VarCovError('not implemented for "nlme" objects')
    if len(obj.groups) > 1:
        raise VarCovError("not implemented for multiple levels of nesting")

    sigma = float(obj.sigma)
    re_block = obj.modelStruct.reStruct[0]
    d = np.asarray(re_block.as_matrix, dtype=np.float64) * (sigma**2)

    if type == "random.effects":
        result_values: np.ndarray | list[tuple[str, np.ndarray]] = d
    else:
        result_values = []
        groups = np.asarray(obj.groups[0], dtype=object)
        ugroups = _unique_preserve(groups)
        if individuals is _MISSING:
            chosen = (ugroups[0],)
        elif isinstance(individuals, (int, np.integer)) or (
            isinstance(individuals, float) and float(individuals).is_integer()
        ):
            index = int(individuals)
            if index < 1 or index > len(ugroups):
                raise IndexError("subscript out of bounds")
            chosen = (ugroups[index - 1],)
        else:
            if isinstance(individuals, (str, bytes)):
                chosen = (individuals,)
            else:
                chosen = tuple(str(item) for item in individuals)

        cs_t = obj.modelStruct.corStruct
        var_struct = obj.modelStruct.varStruct
        for individ in (str(item) for item in chosen):
            ind = groups == individ
            ni = int(np.sum(ind))
            if ni == 0:
                raise VarCovError(f"individual {individ!r} was not used in the fit")
            if cs_t is not None and ni > 1:
                v = _cor_matrix_entry(cs_t, individ)
            else:
                v = np.eye(ni, dtype=np.float64)
            if var_struct is not None:
                if cs_t is not None:
                    grp = _get_groups(cs_t)
                else:
                    order = np.argsort(groups, kind="mergesort")
                    grp = groups[order]
                weights = _var_weights(var_struct)
                sds = 1.0 / weights[grp == individ]
            else:
                sds = np.ones(ni, dtype=np.float64)
            sds = sigma * np.asarray(sds, dtype=np.float64)
            cond_var = (v * sds[:, None]) * sds[None, :]
            nrows = cond_var.shape[0]
            cond_var = np.array(cond_var, dtype=np.float64, copy=True)
            cond_var.setflags(write=True)
            # R sets dimnames to 1:nrow; values are unchanged.

            if type == "conditional":
                result_values.append((individ, cond_var))
            else:
                z = _random_design(
                    obj.modelStruct.reStruct,
                    _get_data(obj),
                    ind,
                )
                marginal = cond_var + z @ d @ z.T
                result_values.append((individ, marginal))

    group_levels = tuple(str(name) for name in obj.group_names)
    if type == "random.effects":
        assert isinstance(result_values, np.ndarray)
        return VarCovMatrix(result_values, (type, "VarCov"), group_levels)
    assert isinstance(result_values, list)
    return VarCovList(tuple(result_values), (type, "VarCov"), group_levels)


def _get_var_cov_gls(obj: Gls, individual: Any) -> VarCovMatrix:
    cs_t = obj.modelStruct.corStruct
    if cs_t is None:
        raise VarCovError("not implemented for uncorrelated errors")
    grp = _get_groups(cs_t)
    if grp is None:
        raise VarCovError("not implemented for correlation structures without a grouping factor")

    if isinstance(individual, (int, np.integer)) or (
        isinstance(individual, float) and float(individual).is_integer()
    ):
        ind = np.asarray(grp, dtype=np.int64) == int(individual)
        individ_key: str | int = int(individual)
    else:
        ind = np.asarray(grp, dtype=object) == individual
        individ_key = individual

    ni = int(np.sum(ind))
    if ni == 0:
        raise VarCovError(f"individual {individual!r} was not used in the fit")

    if ni > 1:
        s = _cor_matrix_entry(cs_t, individ_key)
    else:
        s = np.eye(1, dtype=np.float64)

    var_struct = obj.modelStruct.varStruct
    if var_struct is not None:
        vw = 1.0 / _var_weights(var_struct)
        vw = np.asarray(vw, dtype=np.float64)[ind]
    else:
        vw = np.ones(ni, dtype=np.float64)
    vars_ = (float(obj.sigma) * vw) ** 2
    sqrt_vars = np.sqrt(vars_)
    result = (s * sqrt_vars[:, None]) * sqrt_vars[None, :]
    group_levels = tuple(str(name) for name in obj.group_names)
    return VarCovMatrix(result, ("marginal", "VarCov"), group_levels)


def _cor_matrix_entry(cor_struct: Any, individ: Any) -> np.ndarray:
    matrices = getattr(cor_struct, "cor_matrices", None)
    if matrices is not None:
        key = individ
        if key not in matrices and str(key) in matrices:
            key = str(key)
        return np.asarray(matrices[key], dtype=np.float64)
    cor_matrix = getattr(cor_struct, "corMatrix", None)
    if callable(cor_matrix):
        full = cor_matrix()
        if isinstance(full, dict):
            key = individ if individ in full else str(individ)
            return np.asarray(full[key], dtype=np.float64)
        if isinstance(full, (list, tuple)):
            index = int(individ) - 1 if isinstance(individ, int) else individ
            return np.asarray(full[index], dtype=np.float64)
    raise TypeError(f"corStruct stand-in lacks cor matrices for {individ!r}")


def _var_weights(var_struct: Any) -> np.ndarray:
    weights = getattr(var_struct, "var_weights", None)
    if weights is not None:
        return np.asarray(weights, dtype=np.float64)
    fn = getattr(var_struct, "varWeights", None)
    if callable(fn):
        return np.asarray(fn(), dtype=np.float64)
    raise TypeError("varStruct stand-in lacks var weights")


def _get_groups(cor_struct: Any) -> np.ndarray | None:
    groups = getattr(cor_struct, "groups", None)
    if groups is not None:
        return np.asarray(groups)
    fn = getattr(cor_struct, "getGroups", None)
    if callable(fn):
        return np.asarray(fn())
    return None


def _get_data(obj: Lme) -> Any:
    if obj.data is None:
        raise VarCovError("lme stand-in lacks data for conditional or marginal variance")
    return obj.data


def _random_design(re_struct: tuple[ReStructBlock, ...], data: Any, ind: np.ndarray) -> np.ndarray:
    block = re_struct[0]
    model_matrix = getattr(block, "model_matrix", None)
    if callable(model_matrix):
        full = np.asarray(model_matrix(data), dtype=np.float64)
        return full[ind, :]
    raise VarCovError("reStruct stand-in lacks model.matrix for marginal variance")


def _unique_preserve(values: np.ndarray) -> tuple[Any, ...]:
    seen: list[Any] = []
    for item in values:
        if item not in seen:
            seen.append(item)
    return tuple(seen)


def _match_arg(value: str, choices: Sequence[str]) -> str:
    if value in choices:
        return value
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise VarCovError(f"'{value}' is abbreviated")
    shown = ", ".join(repr(choice) for choice in choices)
    raise VarCovError(f"'{value}' should be one of {shown}")


def _class_vector(object: Any) -> tuple[str, ...]:
    classes = getattr(object, "classes", None)
    if classes is not None:
        return tuple(classes)
    return (type(object).__name__,)


def _show_classes(classes: tuple[str, ...]) -> str:
    if len(classes) == 1:
        return f'"{classes[0]}"'
    inner = ", ".join(f"'{name}'" for name in classes)
    return f'"c({inner})"'
