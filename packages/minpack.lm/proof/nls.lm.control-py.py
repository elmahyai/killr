import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from minpacklm.nls_lm_control import nls_lm_control


def pack(ctrl):
    diag = ctrl["diag"]
    diag_is_list = isinstance(diag, list)
    if diag is None:
        diag_vals = []
        diag_len = 0
    elif isinstance(diag, np.ndarray):
        diag_vals = [float(item) for item in np.ravel(diag)]
        diag_len = int(diag.size)
    elif isinstance(diag, (list, tuple)):
        diag_vals = [float(item) for item in diag]
        diag_len = len(diag)
    else:
        diag_vals = [float(diag)]
        diag_len = 1
    maxfev = ctrl["maxfev"]
    maxfev_is_int = _is_integer(maxfev)
    if isinstance(maxfev, np.ndarray):
        maxfev_vals = [float(item) for item in np.ravel(maxfev)]
    elif isinstance(maxfev, (list, tuple)):
        maxfev_vals = [float(item) for item in maxfev]
    elif maxfev is None:
        maxfev_vals = []
    else:
        maxfev_vals = [float(maxfev)]
    return [
        float(ctrl["ftol"]),
        float(ctrl["ptol"]),
        float(ctrl["gtol"]),
        float(ctrl["epsfcn"]),
        float(ctrl["factor"]),
        float(ctrl["maxiter"]),
        float(ctrl["nprint"]),
        1.0 if diag_is_list else 0.0,
        float(diag_len),
        *diag_vals,
        1.0 if maxfev_is_int else 0.0,
        float(len(maxfev_vals)),
        *maxfev_vals,
    ]


def _is_integer(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.integer)


def one():
    defaults = nls_lm_control()
    example = nls_lm_control(maxiter=4)
    positional = nls_lm_control(1e-4, 1e-5)
    numeric_diag = nls_lm_control(
        ftol=1e-6,
        ptol=1e-7,
        gtol=1e-5,
        diag=np.array([1.5, 2.5, 3.5]),
        epsfcn=1e-8,
        factor=10,
        maxfev=200.0,
        maxiter=4,
        nprint=1,
    )
    integer_maxfev = nls_lm_control(
        diag=[2, 4],
        maxfev=200,
        maxiter=4,
        nprint=1,
    )
    packed = []
    for ctrl in (defaults, example, positional, numeric_diag, integer_maxfev):
        packed.extend(pack(ctrl))
    return packed


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (
        ",".join("%.17g" % float(part) for part in value),
        statistics.median(elapsed),
    )
)
