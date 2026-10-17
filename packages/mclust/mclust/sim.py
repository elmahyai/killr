"""Translation of mclust ``sim``: dispatch to ``sim<modelName>`` after ``checkModelName``.

Only the sim functions in this package are reachable. Other models stop with NotImplementedError.
"""

from __future__ import annotations

from typing import Any

from mclust.model_metadata import checkModelName
from mclust.sim_e import simE
from mclust.sim_eee import simEEE
from mclust.sim_eei import simEEI
from mclust.sim_eev import simEEV
from mclust.sim_eii import simEII
from mclust.sim_evi import simEVI
from mclust.sim_v import simV
from mclust.sim_vei import simVEI

_ALIASES = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}
_SIM = {
    "E": simE,
    "V": simV,
    "EII": simEII,
    "EEI": simEEI,
    "EEE": simEEE,
    "EEV": simEEV,
    "EVI": simEVI,
    "VEI": simVEI,
}


def sim(modelName: str, parameters: dict[str, Any], n: int, seed: Any = None, **kwargs: Any):
    modelName = _ALIASES.get(modelName, modelName)
    checkModelName(modelName)
    if modelName not in _SIM:
        raise NotImplementedError(f"sim{modelName} is not translated")
    return _SIM[modelName](parameters, n, seed=seed, **kwargs)
