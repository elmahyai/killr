"""Verification (not recorded): mclust.bic_family.mclustBIC with G = 1:9 against R mclust 6.1.3.

Run from packages/mclust, after proof/mclustBIC-G19-r.R:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/mclustBIC-G19-py.py
Writes docs/output/mclustBIC-G19-py.txt with the same record layout as mclustBIC-G19-r.txt.
"""

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mclust.bic_family import mclustBIC  # noqa: E402
sys.path.insert(0, str(ROOT.parent / "boot"))
from boot.rng import set_seed  # noqa: E402

xa_bank = np.loadtxt(ROOT / "proof" / "mclust_fit_banknote6.csv", delimiter=",")
ib = np.arange(1, 61)
xb = np.column_stack([((ib * 37) % 11) / 11 + 0.05 * ib / 60,
                      ((ib * 23) % 13) / 13 - 0.1 * ib / 60])
ia = np.arange(1, 41)
xc = ((ia * 37) % 11) / 11 + 0.1 * ia / 40
xf = np.concatenate([((ia * 37) % 11) / 11 + 0.1 * ia / 40, 5 + ((ia * 23) % 13) / 13 - 0.1 * ia / 40])
xfa = np.loadtxt(ROOT / "proof" / "mclust_faithful.csv", delimiter=",")
ig = np.arange(1, 2401)
xg = np.column_stack([np.sin(0.37 * ig + 1.3) + 0.4 * np.cos(0.11 * ig) + 3.0 * (ig > 1200),
                      np.cos(0.23 * ig) + 0.5 * np.sin(0.07 * ig)])
noise_b = [3, 17, 29, 44, 58]
noise_c = [2, 5, 9]


def fmt(v):
    v = float(v)
    if math.isnan(v):
        return "NA"
    return "%.17g" % v


def one():
    return {
        "A": mclustBIC(xa_bank, G=list(range(1, 10))),
        "B": mclustBIC(xb, G=list(range(1, 10))),
        "C": mclustBIC(xc, G=list(range(1, 10))),
        "D": mclustBIC(xb, G=list(range(1, 10)), modelNames=["EII", "VII", "EEE", "VVV"]),
        "E": mclustBIC(xc, G=list(range(1, 10)), modelNames=["E", "V"]),
        "F": mclustBIC(xf, G=list(range(1, 10))),
        "FA": mclustBIC(xfa, G=list(range(1, 10))),
        "BIG": (set_seed(2026), mclustBIC(xg, G=list(range(1, 10))))[1],
        "NB": mclustBIC(xb, G=list(range(1, 10)), initialization={"noise": noise_b}),
        "NC": mclustBIC(xc, G=list(range(1, 10)), initialization={"noise": noise_c}),
        "NBV": mclustBIC(xb, G=list(range(1, 10)), initialization={"noise": noise_b}, Vinv=0.5),
    }


if __name__ == "__main__":
    fits = one()
    lines = []
    for k in ["A", "B", "C", "D", "E", "F", "FA", "BIG", "NB", "NC", "NBV"]:
        b = fits[k]
        vals = np.asarray(b["values"], dtype=float)
        codes = np.asarray(b["returnCodes"], dtype=float)
        dims = [vals.shape[0], vals.shape[1]]
        lines.append("\t".join([f"{k}", "BIC"] + [fmt(v) for v in dims]))
        lines.append("\t".join([f"{k}", "BICdim"] + [fmt(v) for v in dims]))
        lines.append("\t".join([f"{k}", "values"] + [fmt(v) for v in vals.ravel(order="F")]))
        lines.append("\t".join([f"{k}", "returnCodes"] + [fmt(v) for v in codes.ravel(order="F")]))
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000.0)
    lines.append(f"time_ms\t{'%.17g' % statistics.median(elapsed)}")
    out = ROOT / "docs" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "mclustBIC-G19-py.txt").write_text("\n".join(lines) + "\n")
    print("Python mclustBIC G=1:9 median ms:", statistics.median(elapsed))
