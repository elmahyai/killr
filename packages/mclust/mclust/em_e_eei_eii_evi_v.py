"""EM wrappers for the E, EEI, EII, EVI, and V models of mclust 6.1.3 (mclust.R).

``emEEI``, ``emEII``, ``emEVI``, and ``emV`` run the matching E-step to get
``z``, replace ``z`` with the ``z`` from the matching ``me`` routine, and return
the ``mstep`` list. ``emE`` differs as the R code does: its last call is ``meE``,
not ``mstepE``, so it returns the ``meE`` list.
"""

from __future__ import annotations

from typing import Any

from mclust.estep_e import estepE
from mclust.estep_eei import estepEEI
from mclust.estep_eii import estepEII
from mclust.estep_evi import estepEVI
from mclust.estep_v_vei_vev_vii_vvi_vvv import estepV
from mclust.me_e import meE
from mclust.me_eei import meEEI
from mclust.me_eii import meEII
from mclust.me_evi import meEVI
from mclust.me_v import me_v
from mclust.mstep_models import mstepEEI, mstepEII, mstepEVI, mstepV

__all__ = ["emE", "emEEI", "emEII", "emEVI", "emV"]


def _em(estep: Any, me: Any, mstep: Any, data: Any, parameters: dict[str, Any],
        prior: Any, control: Any, warn: bool | None) -> dict[str, Any]:
    z = estep(data, parameters, warn=warn)["z"]
    z = me(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )["z"]
    return mstep(data, z, prior=prior, warn=warn)


def emE(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the E model (`emE` in mclust 6.1.3). The last call is `meE`, as in R."""
    z = estepE(data, parameters, warn=warn)["z"]
    z = meE(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )["z"]
    return meE(data, z, prior=prior, warn=warn)


def emEEI(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the EEI model (`emEEI` in mclust 6.1.3)."""
    return _em(estepEEI, meEEI, mstepEEI, data, parameters, prior, control, warn)


def emEII(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the EII model (`emEII` in mclust 6.1.3)."""
    return _em(estepEII, meEII, mstepEII, data, parameters, prior, control, warn)


def emEVI(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the EVI model (`emEVI` in mclust 6.1.3)."""
    return _em(estepEVI, meEVI, mstepEVI, data, parameters, prior, control, warn)


def emV(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the V model (`emV` in mclust 6.1.3)."""
    return _em(estepV, me_v, mstepV, data, parameters, prior, control, warn)
