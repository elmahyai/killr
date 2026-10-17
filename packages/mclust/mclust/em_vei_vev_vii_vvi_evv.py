"""EM wrappers for the VEI, VEV, VII, VVI, and EVV models of mclust 6.1.3.

``emVEI``, ``emVII``, and ``emVVI`` run the matching E-step to get ``z``, replace
``z`` with the ``z`` from the matching ``me`` routine, and return the ``mstep``
list. ``emVEV`` runs its second ``meVEV`` call without ``Vinv``, as the R code
does, and returns that ``meVEV`` list. ``emEVV`` returns the ``meEVV`` list.
"""

from __future__ import annotations

from typing import Any

from mclust.estep_evv import estepEVV
from mclust.estep_v_vei_vev_vii_vvi_vvv import estepVEI, estepVEV, estepVII, estepVVI
from mclust.me_evv import me_evv
from mclust.me_vei import me_vei
from mclust.me_vev import me_vev
from mclust.me_vii import me_vii
from mclust.me_vvi import me_vvi
from mclust.mstep_vei_vii_vvi import mstep_vei, mstep_vii, mstep_vvi

__all__ = ["emVEI", "emVEV", "emVII", "emVVI", "emEVV"]


def emVEI(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the VEI model (`emVEI` in mclust 6.1.3)."""
    z = estepVEI(data, parameters, warn=warn)["z"]
    z = me_vei(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )["z"]
    return mstep_vei(data, z, prior=prior, warn=warn, control=control)


def emVEV(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the VEV model (`emVEV` in mclust 6.1.3). The last call is `meVEV`, as in R."""
    z = estepVEV(data, parameters, warn=warn)["z"]
    z = me_vev(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )["z"]
    return me_vev(data, z, prior=prior, control=control, warn=warn)


def emVII(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the VII model (`emVII` in mclust 6.1.3)."""
    z = estepVII(data, parameters, warn=warn)["z"]
    z = me_vii(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )["z"]
    return mstep_vii(data, z, prior=prior, warn=warn)


def emVVI(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the VVI model (`emVVI` in mclust 6.1.3)."""
    z = estepVVI(data, parameters, warn=warn)["z"]
    z = me_vvi(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )["z"]
    return mstep_vvi(data, z, prior=prior, warn=warn)


def emEVV(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the EVV model (`emEVV` in mclust 6.1.3). It returns the `meEVV` list, as in R."""
    z = estepEVV(data, parameters, warn=warn)["z"]
    return me_evv(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )
