"""Write the fixed design matrix shared by the R and Python proofs.

Run once. The output is design.csv, with columns y, x1..xp (no intercept).
The R script (r_proof.R) and the Python script (rust_proof.py) both read it.
"""

from pathlib import Path

import numpy as np

N_ROWS = 200
N_PREDICTORS = 12
SEED = 20261017

HERE = Path(__file__).resolve().parent


def main() -> None:
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal((N_ROWS, N_PREDICTORS))
    # Correlate some columns so the best subsets are not trivial.
    x[:, 1] = 0.8 * x[:, 0] + 0.6 * x[:, 1]
    x[:, 5] = 0.7 * x[:, 4] + 0.7 * x[:, 5]
    x[:, 9] = 0.5 * x[:, 2] - 0.5 * x[:, 9]
    beta = np.zeros(N_PREDICTORS)
    beta[[0, 2, 4, 7]] = [2.0, -1.5, 1.0, 0.8]
    y = 1.0 + x @ beta + 0.7 * rng.standard_normal(N_ROWS)

    header = ["y"] + [f"x{j + 1}" for j in range(N_PREDICTORS)]
    data = np.column_stack([y, x])
    out = HERE / "design.csv"
    with out.open("w") as fh:
        fh.write(",".join(header) + "\n")
        for row in data:
            fh.write(",".join(f"{v:.17g}" for v in row) + "\n")
    print(f"wrote {out} with {N_ROWS} rows and {N_PREDICTORS} predictors")


if __name__ == "__main__":
    main()
