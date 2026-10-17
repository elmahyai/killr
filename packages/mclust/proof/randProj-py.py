"""Proof for randProj: the drawing of the projection, and the basis, data, means and covariances it returns."""

import numpy as np

from plot_fixtures import make_fixtures
from plot_proof_common import run_proof
from mclust.rand_proj import randProj

fx = make_fixtures()
P3 = {"mean": fx["mu3"], "variance": {"sigma": fx["sig3"]}}


def values_of(log, res):
    # Column-major, as R's as.numeric() reads a matrix or array.
    log.value("basis", np.asarray(res["basis"]).ravel(order="F"))
    log.value("data", np.asarray(res["data"]).ravel(order="F"))
    log.value("mu", np.asarray(res["mu"]).ravel(order="F"))
    log.value("sigma", np.asarray(res["sigma"]).ravel(order="F"))


def classification_case(fig, ax, log):
    res = randProj(fx["data3"], seeds=[42], parameters=P3, classification=fx["cls"],
                   ax=ax, log=log)
    values_of(log, res)


def error_case(fig, ax, log):
    res = randProj(fx["data3"], seeds=[42, 7], parameters=P3, classification=fx["cls"],
                   truth=fx["truth"], what="error", ax=ax, log=log)
    values_of(log, res)


def uncertainty_case(fig, ax, log):
    res = randProj(fx["data3"], seeds=[3], parameters=P3, z=fx["z"], what="uncertainty",
                   ax=ax, log=log)
    values_of(log, res)


def scale_case(fig, ax, log):
    res = randProj(fx["data3"], seeds=[42], parameters=P3, classification=fx["cls"],
                   scale=True, ax=ax, log=log)
    values_of(log, res)


cases = {
    "classification": classification_case,
    "error": error_case,
    "uncertainty": uncertainty_case,
    "scale": scale_case,
}

if __name__ == "__main__":
    ms = run_proof("randProj", cases, timed="classification")
    print(f"randProj python median ms {ms:.6g}")
