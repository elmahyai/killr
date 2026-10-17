"""Proof for clPairs: the pairs panels, their usr boxes and the points, logged in the shared format."""

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof
from mclust.cl_pairs import clPairs

fx = make_fixtures()

cases = {
    "d3": lambda fig, ax, log: clPairs(fx["data3"], classification=fx["cls"],
                                       fig=fig, ax=ax, log=log),
    "d2": lambda fig, ax, log: clPairs(fx["data2"], classification=fx["cls"],
                                       fig=fig, ax=ax, log=log),
}

if __name__ == "__main__":
    ms = run_proof("clPairs", cases, timed="d3")
    print(f"clPairs python median ms {ms:.6g}")
