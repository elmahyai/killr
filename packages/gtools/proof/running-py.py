import json
import math
import statistics
import sys
import time

import numpy as np

import importlib.util

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
from boot.rng import set_seed
from gtools.running import running

_rng_spec = importlib.util.spec_from_file_location(
    "mass_r_rng",
    "/home/ahmed/killr_projects/killr/packages/MASS/mass/_r_rng.py",
)
_rng_mod = importlib.util.module_from_spec(_rng_spec)
_rng_spec.loader.exec_module(_rng_mod)
norm_rand = _rng_mod.norm_rand


def flat(x):
    if isinstance(x, dict):
        parts = []
        for nm in x:
            parts.append(nm)
            parts.extend(flat(x[nm]))
        return parts
    if isinstance(x, np.ndarray) and x.ndim == 2:
        data = x.reshape(-1, order="F").astype(float)
        return [float(x.shape[0]), float(x.shape[1]), *[float(v) for v in data]]
    if isinstance(x, (list, tuple)):
        if not x:
            return []
        return [float(v) for v in x]
    array = np.asarray(x, dtype=float).reshape(-1)
    if array.size == 0:
        return []
    return [float(v) for v in array]


def sdfun(x, sign=1):
    x = np.asarray(x, dtype=float)
    return float(np.mean(x) + sign * np.sqrt(np.var(x, ddof=1)))


def cor_r(xx, yy):
    a = [float(v) for v in xx]
    b = [float(v) for v in yy]
    if len(a) < 2:
        return math.nan
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    dx = [v - ma for v in a]
    dy = [v - mb for v in b]
    sxx = sum(v * v for v in dx)
    syy = sum(v * v for v in dy)
    if sxx == 0.0 or syy == 0.0:
        return math.nan
    return sum(x * y for x, y in zip(dx, dy)) / math.sqrt(sxx * syy)


def one():
    x = np.arange(1, 21, dtype=float)
    parts = [
        flat(running(x, width=5)),
        flat(running(x, width=5, pad=True)),
        flat(running(x, width=5, align="left", pad=True)),
        flat(running(x, width=5, align="center", pad=True)),
        flat(running(x, width=5, fun=lambda v: v)),
        flat(running(x, width=5, fun=lambda v: v, simplify=False)),
        flat(running(x, width=5, by=5)),
        flat(running(x, width=5, by=2)),
        flat(running(x, width=5, allow_fewer=True, pad=True)),
        flat(running(x, width=5, allow_fewer=False, pad=True)),
    ]
    set_seed(42)
    dat = np.array(
        [(1 + i / 40) * norm_rand() for i in range(1, 41)],
        dtype=float,
    )
    parts.extend(
        [
            flat(running(dat, width=7, pad=True, fun=np.mean)),
            flat(running(dat, width=7, pad=True, fun=sdfun, sign=-1)),
            flat(running(dat, width=7, pad=True, fun=sdfun, sign=1)),
        ]
    )
    sd_y = np.linspace(0, 1, 30)
    xs = np.array([norm_rand() for _ in range(30)], dtype=float)
    ys = []
    for s in sd_y:
        if s == 0.0:
            ys.append(0.0)
        else:
            ys.append(s * norm_rand())
    ys = np.array(ys, dtype=float)
    parts.append(flat(running(xs, ys, width=9, fun=cor_r, pad=True)))
    out = []
    for part in parts:
        out.extend(part)
    return out


invisible = running(np.arange(1, 4, dtype=float), width=3)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
