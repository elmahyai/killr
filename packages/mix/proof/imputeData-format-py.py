"""Proof: the seven-digit formatting of imputeData's data-frame path against R's format().

Builds the same 20 vectors as imputeData-format-r.R, applies the port's `_r_format_digits`,
and prints one line per vector in the same layout as the R output. The vectors and the
arithmetic are identical, so the two outputs can be compared line by line.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.imputeData import _r_format_digits  # noqa: E402

SCALES = [1e-9, 1e-6, 1e-3, 1.0, 1e3, 1e6, 1e9, 1e-12, 1e12]


def vec(k):
    out = []
    for j in range(1, 38):
        base = ((j * (7 * k + 3) + k * k * 13) % 1009) - 504
        s = SCALES[((j + k) % 9)]
        den = 7 if k % 2 == 0 else 3
        x = base / den * s
        if k % 5 == 0:
            x = float(round(x))  # R's round(): half to even, as Python's round()
        if j % 11 == 0:
            x = float("nan")
        out.append(x)
    return np.array(out)


def fmt(v):
    return "NA" if np.isnan(v) else "%.17g" % v


for k in range(1, 21):
    out = _r_format_digits(vec(k))
    print(" ".join(fmt(v) for v in out))
