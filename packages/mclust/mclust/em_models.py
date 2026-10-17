"""EM wrappers for the VEE, EVE, and VVE models of mclust 6.1.3 (mclust2.R).

``emVEE``, ``emEVE``, and ``emVVE`` mirror the R functions of the same name.
Each one runs the matching E-step (``estepVEE``, ``estepEVE``, ``estepVVE``)
to get ``z``, then calls the matching EM routine (``meVEE``, ``meEVE``,
``meVVE``) with the parameters' ``Vinv``, as the R wrappers do.
"""

from __future__ import annotations

from typing import Any

from mclust.estep_vee_eve_vve import estep_eve, estep_vee, estep_vve
from mclust.me_models import meEVE, meVEE, meVVE

__all__ = ["emVEE", "emEVE", "emVVE"]


def _em(
    estep: Any,
    me: Any,
    data: Any,
    parameters: dict[str, Any],
    prior: Any,
    control: Any,
    warn: bool | None,
) -> dict[str, Any]:
    z = estep(data, parameters, warn=warn)["z"]
    return me(
        data,
        z,
        prior=prior,
        control=control,
        Vinv=parameters.get("Vinv"),
        warn=warn,
    )


def emVEE(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the VEE model (`emVEE` in mclust 6.1.3)."""
    return _em(estep_vee, meVEE, data, parameters, prior, control, warn)


def emEVE(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the EVE model (`emEVE` in mclust 6.1.3)."""
    return _em(estep_eve, meEVE, data, parameters, prior, control, warn)


def emVVE(data, parameters, prior=None, control=None, warn=None, **kwargs: Any) -> dict[str, Any]:
    """EM step for the VVE model (`emVVE` in mclust 6.1.3)."""
    return _em(estep_vve, meVVE, data, parameters, prior, control, warn)
