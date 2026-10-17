"""EM wrappers for the EEE, EEV, and VVV models of mclust 6.1.3.

Each function takes ``z`` from the E-step, replaces it with ``z`` from the
matching ``me`` routine, and returns the ``mstep`` list.
"""

from __future__ import annotations

from typing import Any

from mclust.estep_eee import estepEEE
from mclust.estep_eev import estepEEV
from mclust.estep_v_vei_vev_vii_vvi_vvv import estepVVV
from mclust.me_eee_ev_xxx import meEEE, meEEV
from mclust.me_vvv import me_vvv
from mclust.mstep_eee_ev_vv import mstepEEE, mstepEEV, mstepVVV

__all__ = ["emEEE", "emEEV", "emVVV"]


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


def emEEE(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the EEE model (`emEEE` in mclust 6.1.3)."""
    return _em(estepEEE, meEEE, mstepEEE, data, parameters, prior, control, warn)


def emEEV(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the EEV model (`emEEV` in mclust 6.1.3)."""
    return _em(estepEEV, meEEV, mstepEEV, data, parameters, prior, control, warn)


def emVVV(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the VVV model (`emVVV` in mclust 6.1.3)."""
    return _em(estepVVV, me_vvv, mstepVVV, data, parameters, prior, control, warn)
