"""Translation of mclust ``estep``: the E-step generic that dispatches on ``modelName``.

R's ``estep`` checks the model name, then calls ``estep<modelName>`` with the same
data, parameters, and warn. The aliases ``X``, ``XII``, ``XXI``, and ``XXX`` pass the
check but have no ``estepX`` function in mclust, so R stops with "could not find
function". The same error is raised here.
"""

from __future__ import annotations

from typing import Any, Callable

from mclust.estep_e import estepE
from mclust.estep_eee import estepEEE
from mclust.estep_eei import estepEEI
from mclust.estep_eev import estepEEV
from mclust.estep_eii import estepEII
from mclust.estep_evi import estepEVI
from mclust.estep_evv import estepEVV
from mclust.estep_v_vei_vev_vii_vvi_vvv import (
    estepV,
    estepVEI,
    estepVEV,
    estepVII,
    estepVVI,
    estepVVV,
)
from mclust.estep_vee_eve_vve import estep_eve, estep_vee, estep_vve
from mclust.model_metadata import checkModelName

__all__ = ["estep"]

_ESTEP_BY_MODEL: dict[str, Callable[..., dict[str, Any]]] = {
    "E": estepE,
    "V": estepV,
    "EII": estepEII,
    "VII": estepVII,
    "EEI": estepEEI,
    "VEI": estepVEI,
    "EVI": estepEVI,
    "VVI": estepVVI,
    "EEE": estepEEE,
    "EVE": estep_eve,
    "VEE": estep_vee,
    "VVE": estep_vve,
    "EEV": estepEEV,
    "VEV": estepVEV,
    "EVV": estepEVV,
    "VVV": estepVVV,
}


def estep(data: Any, modelName: str, parameters: dict[str, Any], warn: bool | None = None) -> dict[str, Any]:
    """R: estep(data, modelName, parameters, warn = NULL, ...).

    The R ``...`` arguments are not taken: none of the model functions uses them.
    """
    checkModelName(modelName)
    fn = _ESTEP_BY_MODEL.get(modelName)
    if fn is None:
        raise ValueError(f"could not find function \"estep{modelName}\"")
    return fn(data, parameters, warn)
