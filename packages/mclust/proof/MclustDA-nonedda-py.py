"""Proof of non-EDDA MclustDA classification against R.

The fixture has three classes, each selected by MclustDA with two components.
Timing is one untimed call followed by the median of 20 calls.
"""

import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mclust_da import mclust_da  # noqa: E402
from mclust.predict_mclust_da import predict_mclust_da  # noqa: E402

PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"


def make_data():
    n = 60
    t = np.arange(n, dtype=float)
    centers = [(-3.0, -3.0), (3.0, 3.0), (-3.0, 3.0)]
    rows = []
    labels = []
    for i, (cx, cy) in enumerate(centers, start=1):
        rows.append(
            np.column_stack(
                [
                    cx + 0.45 * np.sin(t * 0.71) + np.where(t < 30, -0.8, 0.8),
                    cy + 0.45 * np.cos(t * 0.53) + np.where(t < 30, 0.7, -0.7),
                ]
            )
        )
        labels.extend([str(i)] * n)
    return np.vstack(rows), np.asarray(labels, dtype=object)


X, classes = make_data()


def one():
    fit = mclust_da(
        X,
        classes,
        G=[1, 2, 3],
        model_names=["EEE", "VEI"],
        model_type="MclustDA",
    )
    return fit, predict_mclust_da(fit)


fit, value = one()  # untimed call
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

r_labels = [
    line.strip().strip('"')
    for line in (PROOF / "MclustDA-nonedda-r-labels.txt").read_text().splitlines()
    if line.strip()
]
with (PROOF / "MclustDA-nonedda-r-z.csv").open(newline="") as handle:
    r_z = np.asarray([[float(x) for x in row] for row in csv.reader(handle)])
r_ms = float((PROOF / "MclustDA-nonedda-r-ms.txt").read_text())
labels = value["classification"].astype(str).tolist()
max_abs_diff = float(np.max(np.abs(value["z"] - r_z)))
matches = labels == r_labels and max_abs_diff <= 1e-8
translated_ms = statistics.median(elapsed)
speedup = r_ms / translated_ms

(OUTPUT / "MclustDA-nonedda-py.txt").write_text(
    "\n".join(
        [
            "MclustDA non-EDDA classification",
            "components " + "/".join(str(m["G"]) for m in fit["models"].values()),
            f"matches {'true' if matches else 'false'}",
            f"max_abs_diff {max_abs_diff:.17g}",
            f"r_ms {r_ms:.17g}",
            f"translated_ms {translated_ms:.17g}",
            f"speedup {speedup:.17g}",
        ]
    )
    + "\n"
)
print(f"matches {'true' if matches else 'false'}")
print(f"max_abs_diff {max_abs_diff:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {translated_ms:.17g}")
print(f"speedup {speedup:.17g}")
