"""Proof for mclust1Dplot: the classification, error, uncertainty and density drawings, logged in the shared format."""

import numpy as np

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof
from mclust.mclust_1d_plot import mclust1Dplot

fx = make_fixtures()
x1 = fx["data3"][:, 0]
P1 = {
    "mean": np.array([[0.2, 2.4, 1.1]]),
    "pro": fx["pro"],
    "variance": {"sigmasq": np.array([0.8, 0.5, 0.6]), "G": 3},
}

cases = {
    "classification": lambda fig, ax, log: mclust1Dplot(
        x1, classification=fx["cls"], ax=ax, log=log),
    "error": lambda fig, ax, log: mclust1Dplot(
        x1, classification=fx["cls"], truth=fx["truth"], what="error", ax=ax, log=log),
    "uncertainty": lambda fig, ax, log: mclust1Dplot(
        x1, z=fx["z"], what="uncertainty", ax=ax, log=log),
    "density": lambda fig, ax, log: mclust1Dplot(
        x1, parameters=P1, what="density", ax=ax, log=log),
}

if __name__ == "__main__":
    ms = run_proof("mclust1Dplot", cases, timed="density")
    print(f"mclust1Dplot python median ms {ms:.6g}")
