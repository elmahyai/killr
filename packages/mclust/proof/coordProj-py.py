"""Proof for coordProj: the projected points and ellipses, logged in the shared format."""

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof
from mclust.coord_proj import coordProj

fx = make_fixtures()
P3 = {"mean": fx["mu3"], "variance": {"sigma": fx["sig3"]}}

cases = {
    "classification": lambda fig, ax, log: coordProj(
        fx["data3"], dimens=(1, 2), parameters=P3, classification=fx["cls"], ax=ax, log=log),
    "error": lambda fig, ax, log: coordProj(
        fx["data3"], dimens=(2, 3), parameters=P3, classification=fx["cls"],
        truth=fx["truth"], what="error", ax=ax, log=log),
    "uncertainty": lambda fig, ax, log: coordProj(
        fx["data3"], dimens=(1, 3), parameters=P3, z=fx["z"], what="uncertainty",
        ax=ax, log=log),
}

if __name__ == "__main__":
    ms = run_proof("coordProj", cases, timed="classification")
    print(f"coordProj python median ms {ms:.6g}")
