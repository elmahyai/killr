import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")

from boot.rng import set_seed
from statmod.compare_growth_curves import compareGrowthCurves

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
OUT.mkdir(parents=True, exist_ok=True)


def main_group():
    return np.array(["B", "B", "A", "A", "A", "C", "C", "D", None], dtype=object)


def main_y():
    return np.array(
        [
            [1.0, 1.2, 1.1, 0.9],
            [1.1, 1.3, 1.0, 1.0],
            [2.0, 2.1, 1.9, 2.2],
            [2.2, 2.0, 2.3, 2.1],
            [2.1, np.nan, 2.0, 2.0],
            [3.0, 3.2, 3.1, 2.9],
            [3.1, 3.0, np.nan, 3.2],
            [4.0, 4.1, 4.2, 4.0],
            [0.5, 0.4, 0.6, 0.5],
        ],
        dtype=float,
    )


def collect(tab):
    return np.concatenate(
        [
            np.asarray(tab["Stat"], dtype=float),
            np.asarray(tab["P.Value"], dtype=float),
            np.asarray(tab["adj.P.Value"], dtype=float),
        ]
    )


def one():
    import io
    import contextlib

    set_seed(424242)
    with contextlib.redirect_stdout(io.StringIO()):
        main = compareGrowthCurves(main_group(), main_y(), nsim=40, times=[1, 3, 4], verbose=True)
    set_seed(7)
    numeric_groups = compareGrowthCurves(
        np.array([10, 2, 10, 2, 2], dtype=float),
        np.array(
            [
                [5.0, 5.2, 5.1],
                [1.0, 1.4, 1.2],
                [5.3, 4.9, 5.0],
                [1.3, 1.1, 1.5],
                [0.9, 1.2, 1.0],
            ],
            dtype=float,
        ),
        nsim=25,
        verbose=False,
        adjust="bonferroni",
        n0=1,
    )
    set_seed(99)
    chosen = compareGrowthCurves(
        main_group()[:7],
        main_y()[:7, :],
        levels=["C", "A"],
        nsim=15,
        verbose=False,
        adjust="BH",
    )
    return np.concatenate([collect(main), collect(numeric_groups), collect(chosen)])


def _format_table(tab):
    lines = ["  Group1 Group2 Stat P.Value adj.P.Value"]
    for i, stat in enumerate(tab["Stat"]):
        lines.append(
            "%s %s %.17g %.17g %.17g"
            % (
                tab["Group1"][i],
                tab["Group2"][i],
                float(stat),
                float(tab["P.Value"][i]),
                float(tab["adj.P.Value"][i]),
            )
        )
    return "\n".join(lines)


import io
import contextlib

buffer = io.StringIO()
set_seed(424242)
with contextlib.redirect_stdout(buffer):
    example = compareGrowthCurves(main_group(), main_y(), nsim=40, times=[1, 3, 4], verbose=True)
(OUT / "compareGrowthCurves-python.txt").write_text(
    buffer.getvalue() + _format_table(example) + "\n",
    encoding="utf-8",
)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000.0)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
