"""Verify a survreg distribution object (survival::survregDtest)."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

# Names of ``survreg.distributions`` in survival 3.8-12 (reference ``dist`` field).
_SURVREG_DISTRIBUTION_NAMES: frozenset[str] = frozenset(
    {
        "extreme",
        "logistic",
        "gaussian",
        "weibull",
        "exponential",
        "rayleigh",
        "loggaussian",
        "lognormal",
        "loglogistic",
        "t",
    }
)


def _is_function(obj: Any) -> bool:
    return callable(obj) and not isinstance(obj, type)


def _all_equal(
    target: Any,
    current: Any,
    tolerance: float = math.sqrt(np.finfo(float).eps),
) -> bool:
    target_arr = np.asarray(target, dtype=float).ravel()
    current_arr = np.asarray(current, dtype=float).ravel()
    if target_arr.shape != current_arr.shape:
        return False
    target_na = np.isnan(target_arr)
    current_na = np.isnan(current_arr)
    if np.any(target_na != current_na):
        return False
    equal = target_na | (target_arr == current_arr)
    if np.all(equal):
        return True
    target_arr = target_arr[~equal]
    current_arr = current_arr[~equal]
    n = target_arr.size
    scale = float(np.sum(np.abs(target_arr) / n))
    if not (np.isfinite(scale) and scale > tolerance):
        scale = 1.0
    return bool(np.all(np.abs(target_arr - current_arr) <= tolerance * scale))


def _is_character_name(name: Any) -> bool:
    if isinstance(name, str):
        return True
    if isinstance(name, (bytes, np.str_)):
        return True
    return False


def _unlist_parms(parms: Any) -> Any:
    if parms is None:
        return None
    if isinstance(parms, Mapping):
        return list(parms.values())
    if isinstance(parms, (str, bytes)):
        return parms
    if isinstance(parms, np.ndarray):
        return parms.reshape(-1).tolist()
    if isinstance(parms, Sequence):
        out: list[Any] = []
        for item in parms:
            if isinstance(item, Mapping):
                out.extend(item.values())
            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
                out.extend(item)
            else:
                out.append(item)
        return out
    return parms


def _density_matrix_ok(temp: Any) -> bool:
    if not isinstance(temp, np.ndarray):
        return False
    if temp.dtype.kind not in "fiu":
        return False
    if temp.ndim != 2:
        return False
    return temp.shape == (10, 5)


def survregDtest(dlist: Mapping[str, Any], verbose: bool = False) -> bool | list[str]:
    """Return ``True`` if ``dlist`` is a valid survreg distribution object."""
    errlist: list[str] = []

    name = dlist.get("name")
    if name is None:
        errlist.append("Missing a name")
    elif isinstance(name, str):
        pass
    elif isinstance(name, np.ndarray) and name.dtype.kind in ("U", "S") and name.size == 1:
        pass
    elif isinstance(name, (list, tuple)) and len(name) == 1 and _is_character_name(name[0]):
        pass
    else:
        errlist.append("Invalid name")

    dist_ref = dlist.get("dist")
    if dist_ref is not None:
        if not isinstance(dist_ref, str) or dist_ref not in _SURVREG_DISTRIBUTION_NAMES:
            errlist.append("Reference distribution not found")
        else:
            for key, message in (
                ("trans", "Missing or invalid trans component"),
                ("itrans", "Missing or invalid itrans component"),
                ("dtrans", "Missing or invalid dtrans component"),
            ):
                if not _is_function(dlist.get(key)):
                    errlist.append(message)

        if not errlist:
            seq = np.arange(1.0, 11.0, dtype=float)
            trans = dlist["trans"]
            itrans = dlist["itrans"]
            dtrans = dlist["dtrans"]
            if not _all_equal(itrans(trans(seq)), seq):
                errlist.append("trans and itrans must be inverses of each other")
            dtrans_out = dtrans(seq)
            if np.size(dtrans_out) != 10:
                errlist.append("dtrans must be a 1-1 function")
    else:
        for key, message in (
            ("init", "Missing or invalid init function"),
            ("deviance", "Missing or invalid deviance function"),
            ("density", "Missing or invalid density function"),
            ("quantile", "Missing or invalid quantile function"),
        ):
            if key == "density":
                if not _is_function(dlist.get(key)):
                    errlist.append(message)
                else:
                    density = dlist["density"]
                    xtest = np.arange(1.0, 11.0, dtype=float) / 10.0
                    parms = dlist.get("parms")
                    if parms is None:
                        temp = density(xtest)
                    else:
                        temp = density(xtest, _unlist_parms(parms))
                    if not _density_matrix_ok(np.asarray(temp)):
                        errlist.append("Density function must return a 5 column matrix")
            elif not _is_function(dlist.get(key)):
                errlist.append(message)

    if not errlist:
        return True
    if verbose:
        return errlist
    return False
