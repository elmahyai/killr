"""Proof for uncerPlot: the points, lines and misclassification bars, logged in the shared format."""

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof
from mclust.uncer_plot import uncerPlot

fx = make_fixtures()

cases = {
    "no_truth": lambda fig, ax, log: uncerPlot(fx["z"], ax=ax, log=log),
    "with_truth": lambda fig, ax, log: uncerPlot(fx["z"], truth=fx["truth"], ax=ax, log=log),
}

if __name__ == "__main__":
    ms = run_proof("uncerPlot", cases, timed="with_truth")
    print(f"uncerPlot python median ms {ms:.6g}")
