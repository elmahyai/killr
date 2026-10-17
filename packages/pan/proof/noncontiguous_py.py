"""Verify the Python behavior for interleaved subjects.

R pan 2.0 does not reorder subjects: it passes m = length(unique(subj)) to
Fortran, whose contiguous-run walk can abort.  The translated wrappers reject
the same invalid layout before entering the kernel.
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
FIX = HERE / "fixture"
OUT = PKG / "docs" / "output"
sys.path.insert(0, str(PKG))

from pan.mgibbs import mgibbs  # noqa: E402
from pan.mgibbsbd import mgibbsbd  # noqa: E402


def main():
    subj = np.loadtxt(FIX / "subj.csv", dtype=np.int64, ndmin=1)
    pred = np.loadtxt(FIX / "pred.csv", delimiter=",", ndmin=2)
    rows = [line.strip().split(",") for line in (FIX / "y.csv").open()]
    y = np.array([[np.nan if value == "NA" else float(value) for value in row]
                  for row in rows])
    subj = np.resize(np.arange(1, np.unique(subj).size + 1), subj.size)
    common = dict(y=y, subj=subj, pred=pred, xcol=[1, 2, 3], zcol=[1, 2],
                  seed=20261017, iter=1)
    full_prior = dict(a=3.0, Binv=np.eye(2), c=3.0, Dinv=np.eye(4))
    bd_prior = dict(a=3.0, Binv=np.eye(2), c=np.full(2, 3.0),
                    Dinv=np.stack([np.eye(2)] * 2, axis=2))

    lines = [
        "Non-contiguous subject probe (interleaved labels 1,2,1,2,...)",
        "R pan 2.0: native segmentation fault (exit 139), no reordering.",
        "Python mgibbs:",
    ]
    try:
        mgibbs(prior=full_prior, **common)
    except Exception as exc:
        lines.append(f"  {type(exc).__name__}: {exc}")
    else:
        lines.append("  ERROR: call unexpectedly succeeded")
    lines.append("Python mgibbsbd:")
    try:
        mgibbsbd(prior=bd_prior, **common)
    except Exception as exc:
        lines.append(f"  {type(exc).__name__}: {exc}")
    else:
        lines.append("  ERROR: call unexpectedly succeeded")
    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "noncontiguous_compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
