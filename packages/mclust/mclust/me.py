"""``me``: the generic that dispatches the E-step-free M-step update by model.

``me`` mirrors ``me`` in ``R/mclust.R`` (mclust 6.1.3). R checks the model
name, builds the function name ``me<modelName>``, and calls it with the same
arguments. Python does the same through a table. Every ``me*`` function it
calls is already translated and matches R.

The R ``checkModelName`` list has 20 names: the 16 models that take ``z``
(E, V, EII, VII, EEI, VEI, EVI, VVI, EEE, EVE, VEE, VVE, EEV, VEV, EVV, VVV)
and the four single-component fits X, XII, XXI, XXX, which take no ``z``.
For those four R ignores ``z`` and any other extra argument through
``...``. This module does the same.
"""

from __future__ import annotations

from typing import Any

from mclust.me_e import meE
from mclust.me_eee_ev_xxx import meEEE, meEEV
from mclust.me_eei import meEEI
from mclust.me_eii import meEII
from mclust.me_evi import meEVI
from mclust.me_evv import me_evv
from mclust.me_models import meEVE, meVEE, meVVE, meX, meXII, meXXI, meXXX
from mclust.me_v import me_v
from mclust.me_vei import me_vei
from mclust.me_vev import me_vev
from mclust.me_vii import me_vii
from mclust.me_vvi import me_vvi
from mclust.me_vvv import me_vvv

__all__ = ["me"]

# Single-component fits: R's meX, meXII, meXXI, meXXX are emX, emXII, emXXI, emXXX.
_SINGLE = {"X": meX, "XII": meXII, "XXI": meXXI, "XXX": meXXX}

_WITH_Z = {
    "E": meE,
    "V": me_v,
    "EII": meEII,
    "VII": me_vii,
    "EEI": meEEI,
    "VEI": me_vei,
    "EVI": meEVI,
    "VVI": me_vvi,
    "EEE": meEEE,
    "EVE": meEVE,
    "VEE": meVEE,
    "VVE": meVVE,
    "EEV": meEEV,
    "VEV": me_vev,
    "EVV": me_evv,
    "VVV": me_vvv,
}


def me(data: Any, modelName: str, z: Any = None, prior: Any = None,
       control: Any = None, Vinv: Any = None, warn: Any = None, **kwargs: Any) -> dict:
    """Dispatch the M-step-only update (`me` in mclust 6.1.3) to ``me<modelName>``.

    ``modelName`` must be one of the 20 names R's ``checkModelName`` accepts.
    Any other name raises ``ValueError`` with R's message, ``invalid model name``.
    """
    if modelName in _SINGLE:
        # R passes z, control, and Vinv through `...`, where emX and mvnX ignore them.
        return _SINGLE[modelName](data, prior=prior, warn=warn, z=z,
                                  control=control, Vinv=Vinv, **kwargs)
    if modelName in _WITH_Z:
        out = _WITH_Z[modelName](data, z, prior=prior, control=control,
                                 Vinv=Vinv, warn=warn, **kwargs)
        if modelName == "EEE":
            # R's meEEE names the factor `cholSigma`; the Python meEEE says `cholsigma`.
            # Only the name changes here; the values are the meEEE values.
            variance = out["parameters"]["variance"]
            if "cholsigma" in variance and "cholSigma" not in variance:
                variance["cholSigma"] = variance.pop("cholsigma")
        return out
    raise ValueError("invalid model name")
