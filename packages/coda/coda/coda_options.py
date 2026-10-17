"""Query and set options for the codamenu driver (``coda.options`` in coda 0.19-4.1)."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any

import numpy as np

_coda_env_options: dict[str, Any] | None = None


def _bandwidth(x: Any) -> float:
    arr = np.asarray(x, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    n = arr.size
    if n == 0:
        return float("nan")
    sd = float(np.std(arr, ddof=1))
    q75, q25 = np.quantile(arr, [0.75, 0.25])
    iqr = float(q75 - q25) / 1.34
    return 1.06 * min(sd, iqr) * (n**-0.2)


def _default_options() -> dict[str, Any]:
    return {
        "trace": True,
        "densplot": True,
        "lowess": False,
        "combine.plots": True,
        "bandwidth": _bandwidth,
        "digits": 3,
        "quantiles": [0.025, 0.25, 0.5, 0.75, 0.975],
        "frac1": 0.1,
        "frac2": 0.5,
        "q": 0.025,
        "r": 0.005,
        "s": 0.95,
        "combine.stats": False,
        "combine.corr": False,
        "halfwidth": 0.1,
        "user.layout": False,
        "gr.bin": 10,
        "geweke.nbin": 20,
        "gr.max": 50,
    }


def _mode_matches(existing: Any, new: Any) -> bool:
    if callable(existing):
        return callable(new)
    if isinstance(existing, bool):
        return isinstance(new, (bool, np.bool_))
    if isinstance(existing, (int, float, np.floating, np.integer)):
        return isinstance(new, (int, float, np.floating, np.integer)) and not isinstance(
            new, (bool, np.bool_)
        )
    if isinstance(existing, (list, tuple, np.ndarray)):
        return isinstance(new, (list, tuple, np.ndarray))
    return type(existing) is type(new)


def _copy_option_value(value: Any) -> Any:
    if callable(value):
        return value
    if isinstance(value, np.ndarray):
        return value.copy()
    return copy.deepcopy(value)


def _flatten_positional(arg: Any) -> list[Any]:
    if isinstance(arg, np.ndarray):
        if arg.ndim == 0:
            return [arg.item()]
        return list(arg.flat)
    if isinstance(arg, (str, bytes)):
        return [arg]
    if isinstance(arg, Sequence):
        return list(arg)
    return [arg]


def coda_options(*args: Any, **kwargs: Any) -> Any:
    """Get or set coda options the way ``coda.options`` does in R."""
    global _coda_env_options

    if _coda_env_options is None:
        copt = _default_options()
    else:
        copt = _coda_env_options

    if not args and not kwargs:
        return {key: _copy_option_value(val) for key, val in copt.items()}

    call_args: list[tuple[str | None, Any]] = []
    single = False

    if len(args) == 1 and not kwargs:
        only = args[0]
        if isinstance(only, dict):
            call_args = [(key, value) for key, value in only.items()]
        elif isinstance(only, list):
            call_args = [(None, value) for value in only]
        elif isinstance(only, (tuple, np.ndarray)):
            flat = _flatten_positional(only)
            call_args = [(None, value) for value in flat]
            single = True
        else:
            call_args = [(None, only)]
            single = True
    else:
        for arg in args:
            if isinstance(arg, dict):
                call_args.extend((key, value) for key, value in arg.items())
            else:
                call_args.extend((None, item) for item in _flatten_positional(arg))
        call_args.extend(kwargs.items())

    if all(name is None for name, _ in call_args):
        keys = [value for _, value in call_args]
        out: dict[str, Any] = {}
        for key in keys:
            name = str(key)
            if name in copt:
                out[name] = _copy_option_value(copt[name])
        if single:
            first = str(keys[0])
            return out.get(first)
        return out

    working = {key: _copy_option_value(val) for key, val in copt.items()}
    if any(name == "default" and value is True for name, value in call_args if name is not None):
        working = {key: _copy_option_value(val) for key, val in _default_options().items()}

    oldvalue: dict[str, Any] = {}
    for name, value in call_args:
        if name is None or name not in working:
            continue
        oldvalue[name] = _copy_option_value(working[name])
        if value is None:
            working[name] = None
        elif _mode_matches(working[name], value):
            if isinstance(value, np.ndarray):
                working[name] = [float(v) for v in value.tolist()]
            elif isinstance(value, tuple) and isinstance(working[name], list):
                working[name] = [float(v) for v in value]
            else:
                working[name] = value

    _coda_env_options = working
    return oldvalue
