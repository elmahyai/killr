"""Writes the fixed univariate inputs for the proof of pan's ecme().

Run once from anywhere:  python3 packages/pan/proof/make_ecme_fixture.py
Reads subj.csv and pred.csv from fixture/ (written by make_fixture.py) and writes
fixture/ecme_y.csv (complete response), fixture/ecme_occ.csv (occasion 1..n within
each subject) and fixture/ecme_vmax.csv (the nmax x nmax working correlation).
"""

from pathlib import Path

import numpy as np

SEED = 20261018
HERE = Path(__file__).resolve().parent
FIX = HERE / "fixture"


def main() -> None:
    subj = np.loadtxt(FIX / "subj.csv", dtype=np.int64, ndmin=1)
    pred = np.loadtxt(FIX / "pred.csv", delimiter=",", ndmin=2)
    rng = np.random.default_rng(SEED)

    ids, starts, sizes = np.unique(subj, return_index=True, return_counts=True)
    occ = np.concatenate([np.arange(1, n + 1) for n in sizes])
    nmax = int(occ.max())
    ntot = subj.size

    beta = np.array([1.0, 0.5, 0.3])
    b0 = rng.normal(scale=0.6, size=ids.size)
    ar = 0.5 ** np.abs(np.subtract.outer(np.arange(nmax), np.arange(nmax)))
    chol = np.linalg.cholesky(0.8 * ar + 0.2 * np.eye(nmax))
    noise = np.concatenate([chol[:n, :n] @ rng.normal(size=n) for n in sizes])
    y = pred @ beta + np.repeat(b0, sizes) + noise

    np.savetxt(FIX / "ecme_y.csv", y, fmt="%.17g")
    np.savetxt(FIX / "ecme_occ.csv", occ, fmt="%d")
    np.savetxt(FIX / "ecme_vmax.csv", 0.8 * ar + 0.2 * np.eye(nmax), delimiter=",", fmt="%.17g")
    print(f"ntot={ntot} m={ids.size} nmax={nmax}")


if __name__ == "__main__":
    main()
