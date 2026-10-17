"""``em``: the EM generic that dispatches on ``modelName`` (mclust 6.1.3, R/mclust.R).

R's ``em`` checks the model name with ``checkModelName``, builds the function
name ``em<modelName>``, and calls it with the same arguments. Python does the
same through a table. Every ``em*`` function it calls is already translated.

The four single-component models X, XII, XXI, and XXX are ``emX``, ``emXII``,
``emXXI``, and ``emXXX``. They take no ``parameters`` or ``control``, so R's
``...`` swallows them. This module passes them through ``**kwargs`` in the same
way, and the single-component functions ignore them.
"""

from __future__ import annotations

from typing import Any

from mclust.em_control import em_control
from mclust.em_eee_ev_vvv import emEEE, emEEV, emVVV
from mclust.em_e_eei_eii_evi_v import emE, emEEI, emEII, emEVI, emV
from mclust.em_models import emEVE, emVEE, emVVE
from mclust.em_vei_vev_vii_vvi_evv import emEVV, emVEI, emVEV, emVII, emVVI
from mclust.em_x import emX
from mclust.em_xii import emXII
from mclust.em_xxi import emXXI
from mclust.em_xxx import emXXX
from mclust.model_metadata import checkModelName

__all__ = ["em"]

# R's emX, emXII, emXXI, emXXX take data, prior, and warn. Everything else goes to ...
_SINGLE = {"X": emX, "XII": emXII, "XXI": emXXI, "XXX": emXXX}

_WITH_Z = {
    "E": emE,
    "V": emV,
    "EII": emEII,
    "VII": emVII,
    "EEI": emEEI,
    "VEI": emVEI,
    "EVI": emEVI,
    "VVI": emVVI,
    "EEE": emEEE,
    "EVE": emEVE,
    "VEE": emVEE,
    "VVE": emVVE,
    "EEV": emEEV,
    "VEV": emVEV,
    "EVV": emEVV,
    "VVV": emVVV,
}


def em(data: Any, modelName: str, parameters: Any, prior: Any = None,
       control: Any = None, warn: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Run one EM step for ``modelName`` (`em` in mclust 6.1.3).

    ``modelName`` must be one of the 20 names R's ``checkModelName`` accepts.
    Any other name raises ``ValueError`` with R's message, ``invalid model name``.
    When ``control`` is None, the R default ``emControl()`` is used.
    """
    checkModelName(modelName)
    if modelName in _SINGLE:
        return _SINGLE[modelName](data, prior=prior, warn=warn,
                                  parameters=parameters, control=control, **kwargs)
    if control is None:
        control = em_control()
    return _WITH_Z[modelName](data, parameters, prior=prior, control=control,
                              warn=warn, **kwargs)
