"""Writes the fixed inputs shared by the R and Python proofs of pan's mgibbs and mgibbsbd.

Run once from anywhere:  python3 packages/pan/proof/make_fixture.py
Writes packages/pan/proof/fixture/{subj,pred,y}.csv. y has NA for missing values.
"""

from pathlib import Path

import numpy as np

SEED = 20261017
HERE = Path(__file__).resolve().parent
OUT = HERE / "fixture"


def main() -> None:
    rng = np.random.default_rng(SEED)
    m = 40
    sizes = rng.integers(3, 7, size=m)
    subj = np.repeat(np.arange(1, m + 1), sizes)
    ntot = subj.size
    time = np.concatenate([np.arange(n, dtype=float) for n in sizes])
    x = np.repeat(rng.normal(size=m), sizes)
    pred = np.column_stack([np.ones(ntot), time / 2.0, x])  # columns: 1, time, x

    beta_true = np.array([[1.0, 0.5], [0.4, -0.3], [0.3, 0.2]])  # p x r
    b = rng.normal(scale=0.4, size=(m, 2, 2))  # subject x q x r
    chol = np.linalg.cholesky(np.array([[1.0, 0.4], [0.4, 1.0]]))
    eps = rng.normal(size=(ntot, 2)) @ chol.T

    y = pred @ beta_true + eps
    z = pred[:, :2]  # random intercept and time
    for k in range(ntot):
        y[k] += z[k] @ b[subj[k] - 1]

    miss1 = rng.random(ntot) < 0.12
    miss2 = rng.random(ntot) < 0.15
    both = rng.random(ntot) < 0.04
    miss1 |= both
    miss2 |= both
    y[miss1, 0] = np.nan
    y[miss2, 1] = np.nan

    OUT.mkdir(parents=True, exist_ok=True)
    np.savetxt(OUT / "subj.csv", subj, fmt="%d")
    np.savetxt(OUT / "pred.csv", pred, delimiter=",", fmt="%.17g")
    with open(OUT / "y.csv", "w") as fh:
        for row in y:
            fh.write(",".join("NA" if np.isnan(v) else f"{v:.17g}" for v in row) + "\n")

    n_all_missing = int(np.sum(np.isnan(y).all(axis=1)))
    print(f"ntot={ntot} m={m} r=2 pcol=3 p=3 q=2 missing_cells={int(np.isnan(y).sum())} all_missing_rows={n_all_missing}")


if __name__ == "__main__":
    main()
