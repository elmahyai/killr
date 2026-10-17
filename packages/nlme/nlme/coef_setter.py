"""Coefficient assignment for nlme model components (``coef<-`` / ``coefficients<-``)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from nlme.corar1 import CorAR1
from nlme.corarma import CorARMA
from nlme.corcar1 import CorCAR1
from nlme.corident import CorIdent
from nlme.cornatural import CorNatural
from nlme.glsapvar import GlsStruct, _set_coef_model_struct
from nlme.pdmat import PdMat, is_initialized, pdMat
from nlme.restruct import PdMatElement, ReStruct, is_initialized as re_is_initialized
from nlme.var_power import VarPower, set_coef as set_coef_var_power
from nlme.varcomb import VarFunc


def set_coef(object: Any, value) -> Any:
    """Assign coefficients to an nlme structure (R ``coef<-``)."""
    if isinstance(object, CorIdent):
        return object
    if isinstance(object, (CorAR1, CorARMA, CorCAR1, CorNatural)):
        return _set_coef_cor_struct(object, value)
    if isinstance(object, VarPower):
        return set_coef_var_power(object, value)
    if isinstance(object, VarFunc):
        raise TypeError(f"coef<- is not implemented for {type(object)!r}")
    if isinstance(object, PdMat):
        return _set_coef_pd_mat(object, value)
    if isinstance(object, PdMatElement):
        return _set_coef_pd_mat_element(object, value)
    if isinstance(object, ReStruct):
        return _set_coef_restruct(object, value)
    if isinstance(object, GlsStruct):
        _set_coef_model_struct(object, np.asarray(value, dtype=np.float64))
        return object
    raise TypeError(f"do not know how to set coefficients for object of type {type(object)!r}")


def set_coefficients(object: Any, value) -> Any:
    """Alias for ``set_coef`` (R ``coefficients<-`` dispatches to ``coef<-``)."""
    return set_coef(object, value)


def proof_values_coef_assignment() -> np.ndarray:
    """Numeric summary for ``coef<-`` proof (varPower assignment and pdDiag)."""
    from nlme.var_ident import _NlmeFrame
    from nlme.var_power import initialize, proof_values, varPower

    data = _NlmeFrame(
        {
            "y": np.arange(1, 7, dtype=np.float64),
            "x": np.array([1.2, 2.5, 3.1, 4.0, 5.5, 6.3], dtype=np.float64),
        }
    )
    vf = varPower(0.35, form="~x")
    vf = initialize(vf, data)
    vf = set_coef(vf, 0.6)
    vf_part = proof_values(vf)

    pd1 = pdMat(np.diag(np.arange(1, 5, dtype=np.float64)), pdClass="pdDiag")
    pd1 = set_coef(pd1, np.log(np.arange(1, 5, dtype=np.float64)))
    pd_part = np.asarray(pd1.values, dtype=np.float64).ravel()

    cs = CorIdent(np.array([], dtype=np.float64), "~ 1 | Subject", True)
    cs = set_coef(cs, 999.0)
    ident_flag = np.array([1.0], dtype=np.float64)

    return np.concatenate([vf_part, pd_part, ident_flag])


def proof_values_coefficients_assignment() -> np.ndarray:
    """Same case as ``proof_values_coef_assignment`` via ``set_coefficients``."""
    from nlme.var_ident import _NlmeFrame
    from nlme.var_power import initialize, proof_values, varPower

    data = _NlmeFrame(
        {
            "y": np.arange(1, 7, dtype=np.float64),
            "x": np.array([1.2, 2.5, 3.1, 4.0, 5.5, 6.3], dtype=np.float64),
        }
    )
    vf = varPower(0.35, form="~x")
    vf = initialize(vf, data)
    vf = set_coefficients(vf, 0.6)
    return proof_values(vf)


def _set_coef_cor_struct(object: CorAR1 | CorARMA | CorCAR1 | CorNatural, value) -> Any:
    val = np.asarray(value, dtype=np.float64).ravel()
    if isinstance(object.value, float):
        current_len = 1
    else:
        current_len = int(np.asarray(object.value).size)
    if val.size != current_len:
        cls = type(object).__name__
        raise ValueError(f'cannot change the length of the parameter of a "{cls}" object')
    if isinstance(object.value, float):
        return replace(object, value=float(val[0]))
    return replace(object, value=val.copy())


def _set_coef_pd_mat(object: PdMat, value) -> PdMat:
    val = np.asarray(value, dtype=np.float64).ravel()
    if is_initialized(object):
        if val.size != object.values.size:
            raise ValueError("cannot change the length of the parameter after initialization")
        return replace(object, values=val.copy())
    return pdMat(
        val,
        form=object.formula,
        nam=object.names or None,
        pdClass=object.pd_class,
    )


def _set_coef_pd_mat_element(object: PdMatElement, value) -> PdMatElement:
    val = np.asarray(value, dtype=np.float64).ravel()
    if re_is_initialized(object):
        if val.size != object.values.size:
            raise ValueError("cannot change the length of the parameter after initialization")
        return replace(object, values=val.copy())
    return replace(object, values=val.copy())


def _set_coef_restruct(object: ReStruct, value) -> ReStruct:
    if object.plen is None:
        raise ValueError("cannot change the parameter when length of parameters is undefined")
    val = np.asarray(value, dtype=np.float64).ravel()
    if val.size != int(np.sum(object.plen)):
        raise ValueError("cannot change parameter length of initialized objects")
    ends = np.cumsum(object.plen)
    starts = np.concatenate([[0], ends[:-1]])
    new_blocks: list[tuple[str, PdMatElement]] = []
    for index, (name, element) in enumerate(object.blocks):
        chunk = val[starts[index] : ends[index]]
        new_blocks.append((name, set_coef(element, chunk)))
    return ReStruct(new_blocks, object.settings.copy(), object.plen.copy())
