"""Shared steps for mclust meE, meEII, meEEI, and meEVI.

Each public function mirrors the R function of the same name in mclust 6.1.3:
argument checks, the group count from ``Vinv``, the all-missing ``z`` return,
the prior parameters, and the status codes. The numerical work is done by the
``mclust_kernels`` binding built from ``crates/mclust``. Kernel arguments are
given in the order of the R ``.Fortran`` call, and logical flags are 0 or 1.
"""

from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path
from typing import Any

import numpy as np

# signif(.Machine$double.xmax, 6)
SIGNIF_XMAX = 1.79769e308

_LIBRARY = (
    Path(__file__).resolve().parents[3]
    / "crates"
    / "mclust"
    / "target"
    / "release"
    / "libmclust_kernels.so"
)
_KERNELS: Any = None


class _Kernels:
    """Calls a kernel with a list of arguments, which the binding takes as a tuple."""

    def __init__(self, module: Any) -> None:
        self._module = module

    def __getattr__(self, name: str) -> Any:
        fn = getattr(self._module, name)

        def call(args: Any) -> list:
            return fn(tuple(args))

        return call


def kernels() -> _Kernels:
    """Return the ``mclust_kernels`` binding, loading the built library if needed."""
    global _KERNELS
    if _KERNELS is None:
        try:
            import mclust_kernels as module  # an installed binding, if present
        except ImportError:
            if not _LIBRARY.is_file():
                raise ImportError(f"mclust kernels not built: {_LIBRARY}")
            spec = importlib.util.spec_from_file_location("mclust_kernels", _LIBRARY)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        _KERNELS = _Kernels(module)
    return _KERNELS


def first(value: Any) -> Any:
    """R ``x[1]`` for a scalar or a vector."""
    if isinstance(value, (list, tuple, np.ndarray)):
        return np.asarray(value).ravel()[0]
    return value


def logical(value: Any) -> int:
    """R ``as.logical`` of one flag, as the 0 or 1 the kernels expect."""
    return 1 if bool(first(value)) else 0


def r_warning(message: str, warn: bool) -> None:
    if warn:
        warnings.warn(message, RuntimeWarning, stacklevel=3)


def r_diag(x: Any) -> np.ndarray:
    """R ``diag(x)``, including R's rule that a length-one ``x`` gives an identity."""
    v = np.asarray(x, dtype=float).ravel()
    if v.size == 1:
        return np.eye(int(v[0]))
    return np.diag(v)


def column_major(a: Any) -> list[float]:
    """Flatten an array in column-major order, the layout R passes to Fortran."""
    return np.asarray(a, dtype=float).ravel(order="F").tolist()


def fortran_matrix(values: Any, rows: int, cols: int) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape((rows, cols), order="F")


def matrix_data(data: Any, message: str) -> np.ndarray:
    """R's check for a multivariate data matrix with at least two columns."""
    arr = np.asarray(data, dtype=float)
    if arr.ndim != 2 or arr.shape[1] == 1:
        raise ValueError(message)
    return arr


def z_matrix(z: Any, n: int, message: str) -> np.ndarray:
    arr = np.asarray(z, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.shape[0] != n:
        raise ValueError(message)
    return arr


def groups_and_vinv(data: np.ndarray, K: int, Vinv: Any) -> tuple[int, Any]:
    """Number of groups, and Vinv with the R hypervolume default applied."""
    if Vinv is None:
        return K, None
    from mclust.utility_functions import hypvol

    G = K - 1
    if Vinv <= 0:
        Vinv = hypvol(data, reciprocal=True)
    return G, float(Vinv)


def prior_params(prior: dict, data: Any, G: int, model_name: str) -> dict:
    """Call the prior function as R's ``do.call(prior$functionName, ...)`` does."""
    fn = prior["functionName"]
    if isinstance(fn, str):
        from mclust import model_metadata

        fn = getattr(model_metadata, fn)
    extra = {key: value for key, value in prior.items() if key != "functionName"}
    return fn(data=data, G=G, modelName=model_name, **extra)


def below_threshold(equal_pro: bool, warn: bool) -> tuple[str, int]:
    """The message and return code when a mixing or z-sum threshold fails."""
    if equal_pro:
        message, code = "z column sum fell below threshold", -2
    else:
        message, code = "mixing proportion fell below threshold", -3
    r_warning(message, warn)
    return message, code


def iteration_status(its: int, itmax: int, warn: bool) -> tuple[int, int, str | None]:
    """Iteration count, return code, and warning for the normal exit."""
    if its >= itmax:
        r_warning("iteration limit reached", warn)
        return -its, 1, "iteration limit reached"
    return its, 0, None
