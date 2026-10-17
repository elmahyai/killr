"""Proof for errorBars: the arrows R draws, logged in the shared format."""

import numpy as np

from plot_proof_common import run_proof
from mclust.error_bars import errorBars

x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
upper = np.array([2.1, 3.0, 2.5, 4.2, 5.0])
lower = np.array([1.2, 2.0, 1.6, 3.1, 3.9])

cases = {
    "vertical": lambda fig, ax, log: errorBars(x, upper, lower, ax=ax, log=log),
    "horizontal": lambda fig, ax, log: errorBars(
        x, upper, lower, width=0.2, code=2, horizontal=True, ax=ax, log=log),
}

if __name__ == "__main__":
    ms = run_proof("errorBars", cases, timed="vertical")
    print(f"errorBars python median ms {ms:.6g}")
