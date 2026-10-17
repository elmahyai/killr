import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/abind")
from abind.abind import Array
from abind.adrop import adrop
from abind.asub import asub


def flatten(part):
    out = []
    if isinstance(part, Array):
        data = part.data
        names = part.names
        dimnames = part.dimnames
    else:
        data = np.asarray(part)
        names = None
        dimnames = None

    if data.ndim == 0:
        out.extend([0, 1])
        if names is None:
            out.append(0)
        else:
            out.extend([1, *[ord(ch) for ch in "\n".join(str(n) for n in names)]])
        out.append(float(data.reshape(-1)[0]))
        return out

    r_dim = getattr(part, "_r_dim", None) if isinstance(part, Array) else list(data.shape)
    if isinstance(part, Array) and part._r_dim is None and data.ndim == 1:
        out.extend([0, int(data.size)])
        if names is None:
            out.append(0)
        else:
            out.extend([1, *[ord(ch) for ch in "\n".join(str(n) for n in names)]])
        out.extend(float(value) for value in data.reshape(-1))
        return out

    shape = list(r_dim if isinstance(part, Array) and part._r_dim is not None else data.shape)
    out.extend([len(shape), *shape])
    if dimnames is None:
        out.append(0)
    else:
        out.append(1)
        out.append(len(dimnames))
        for margin in dimnames:
            if margin is None:
                out.append(0)
            else:
                out.extend([1, *[ord(ch) for ch in "\n".join(str(n) for n in margin)]])
    out.extend(float(value) for value in np.ravel(data, order="F"))
    return out


def one():
    base = Array(
        np.arange(1, 25, dtype=float).reshape((2, 3, 4), order="F"),
        dimnames=[list("ab"), list("ABC"), list("wxyz")],
    )
    scalar = asub(asub(asub(base, 1, 1, drop=False), 1, 2, drop=False), 1, 3, drop=False)
    parts = [
        adrop(asub(base, 1, 1, drop=False), drop=1),
        adrop(asub(base, 1, 2, drop=False), drop=2),
        adrop(asub(base, 1, 3, drop=False), drop=3),
        adrop(scalar, drop=1),
        adrop(scalar, drop=2),
        adrop(scalar, drop=3),
        adrop(scalar, drop=[1, 2]),
        adrop(scalar, drop=[1, 2], one_d_array=True),
        adrop(scalar, drop=[1, 2], named_vector=False),
        adrop(scalar, drop=None),
        adrop(asub(asub(base, 1, 1, drop=False), 1, 2, drop=False), drop=[False, True, False]),
    ]
    out = []
    for part in parts:
        out.extend(flatten(part))
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
