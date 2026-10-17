"""simulate.Mclust and simulate.densityMclust of mclust 6.1.3 (R/util.R).

R's methods call ``mclust::sim``, which maps the model name (X, XII, XXI, XXX
to E, EII, EEI, EEE), checks it, and calls ``sim<model>``. Here ``sim`` is not
a separate function. The dispatch is written into ``simulate_Mclust``.

The object is a dict with the R fields ``modelName`` and ``parameters``.
``simulate_densityMclust`` drops the ``group`` column, as R's ``[, -1]`` does.

The dispatch covers all 16 models. EVV, VEE, EVE, VVE, VEV, VII, VVI, VVV are
dispatched here; the other eight (E, V, EII, EEI, VEI, EVI, EEE, EEV) go through
``mclust.sim.sim``, which holds those sim functions.
"""

from __future__ import annotations

from typing import Any

from mclust.sim import sim as _sim_dispatch
from mclust.sim_evv_vee_eve_vve import simEVE, simEVV, simVEE, simVVE
from mclust.sim_vev_vii_vvi_vvv import simVEV, simVII, simVVI, simVVV
from mclust._sim_common import SimMatrix

__all__ = ["simulate_Mclust", "simulate_densityMclust"]

_ALIAS = {"X": "E", "XII": "EII", "XXI": "EEI", "XXX": "EEE"}
_VALID = {
    "E", "V", "EII", "VII", "EEI", "VEI", "EVI", "VVI",
    "EEE", "VEE", "EVE", "VVE", "EEV", "VEV", "EVV", "VVV",
}
_TRANSLATED = {
    "VEV": simVEV,
    "VII": simVII,
    "VVI": simVVI,
    "VVV": simVVV,
    "EVV": simEVV,
    "VEE": simVEE,
    "EVE": simEVE,
    "VVE": simVVE,
}


def _sim(model_name: str, parameters: dict[str, Any], n: int, seed: int | None) -> SimMatrix:
    """R ``sim``: map the alias, check the name, then call ``sim<model>``."""
    model = _ALIAS.get(model_name, model_name)
    if model not in _VALID:
        raise ValueError("invalid model name")
    fn = _TRANSLATED.get(model)
    if fn is None:
        return _sim_dispatch(model, parameters, n, seed=seed)
    return fn(parameters, n, seed=seed)


def simulate_Mclust(object_: dict[str, Any], nsim: int = 1, seed: int | None = None, **_: Any) -> SimMatrix:
    """``simulate.Mclust``: n draws from a fitted Mclust model, with the group column."""
    return _sim(object_["modelName"], object_["parameters"], nsim, seed)


def simulate_densityMclust(object_: dict[str, Any], nsim: int = 1, seed: int | None = None, **_: Any) -> SimMatrix:
    """``simulate.densityMclust``: n draws from a density model, without the group column."""
    out = _sim(object_["modelName"], object_["parameters"], nsim, seed)
    colnames = None if out.colnames is None else list(out.colnames)[1:]
    # The group-A sims return _sim_core.SimMatrix (model_name); group B returns _sim_common (modelName).
    model_name = getattr(out, "modelName", None) or getattr(out, "model_name", None)
    return SimMatrix(out[:, 1:], model_name, colnames)
