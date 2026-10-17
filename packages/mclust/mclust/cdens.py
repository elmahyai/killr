"""Translation of mclust ``cdens``: dispatch to the component-density function for a model name.

R maps the univariate and spherical or diagonal aliases first (X to E, XII to EII, XXI to EEI, XXX to EEE),
then calls ``cdens<modelName>``. Each function is called with ``parameters`` by keyword, because the
functions do not take the same positional order (``cdensEVV`` takes ``logarithm`` first).
"""

from __future__ import annotations

from typing import Any

from mclust.cdens_e import cdensE
from mclust.cdens_eee import cdensEEE
from mclust.cdens_eei import cdensEEI
from mclust.cdens_eev import cdensEEV
from mclust.cdens_eii import cdensEII
from mclust.cdens_evi import cdensEVI
from mclust.cdens_evv import cdensEVV
from mclust.cdens_v_vei_vev_vii_vvi_vvv import (
    cdensV,
    cdensVEI,
    cdensVEV,
    cdensVII,
    cdensVVI,
    cdensVVV,
)
from mclust.cdens_vee_eve_vve import cdens_eve, cdens_vee, cdens_vve
from mclust.model_metadata import checkModelName

_ALIASES = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}

_TRANSLATED = {
    "E": cdensE,
    "V": cdensV,
    "EII": cdensEII,
    "VII": cdensVII,
    "EEI": cdensEEI,
    "VEI": cdensVEI,
    "EVI": cdensEVI,
    "VVI": cdensVVI,
    "EEE": cdensEEE,
    "VEE": cdens_vee,
    "EVE": cdens_eve,
    "VVE": cdens_vve,
    "EEV": cdensEEV,
    "VEV": cdensVEV,
    "EVV": cdensEVV,
    "VVV": cdensVVV,
}


def cdens(
    data: Any,
    modelName: str,
    parameters: dict[str, Any],
    logarithm: bool = False,
    warn: bool | None = None,
) -> Any:
    """Return the R ``cdens`` result: an n x G matrix (a dict with ``z`` for the EEE and E-family functions)."""
    name = _ALIASES.get(modelName, modelName)
    checkModelName(name)
    fn = _TRANSLATED.get(name)
    if fn is None:
        raise NotImplementedError(f"cdens{name} is not translated yet")
    return fn(data, parameters=parameters, logarithm=logarithm, warn=warn)
