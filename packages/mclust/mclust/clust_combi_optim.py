"""Optimal combined cluster count from entropy (``clustCombiOptim``)."""

from __future__ import annotations

from typing import Any, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

__all__ = ["clustCombiOptim"]


def clustCombiOptim(object: Any, reg: int = 2, plot: bool = False, **kwargs):
    """Suggest an optimal number of clusters from a ``clustCombi`` object."""
    z = np.asarray(_field(object, "MclustOutput")["z"], dtype=float)
    combi_m = _field(object, "combiM")
    kmax = z.shape[1]
    ent = np.full(kmax, np.nan, dtype=float)
    z0 = z.copy()
    for k in range(kmax, 0, -1):
        z0 = (combi_m[k] @ z0.T).T
        ent[k - 1] = -_sum_xlog(z0)

    if kmax == 2:
        reg = 1
        pcwsreg: dict[str, Any] = {"K": kmax}
    elif reg == 2:
        pcwsreg = _pcws2_reg(np.arange(1, kmax + 1, dtype=float), ent)
    elif reg == 3:
        pcwsreg = _pcws3_reg(np.arange(1, kmax + 1, dtype=float), ent)
    else:
        raise ValueError("reg must be 2 or 3")

    if plot:
        fig, ax = plt.subplots()
        ax.plot(np.arange(1, kmax + 1), ent, **kwargs)
        ax.set_xlabel("Number of clusters")
        ax.set_ylabel("Entropy")
        ax.grid(True)
        ax.set_xticks(np.arange(1, kmax + 1))
        if reg == 2:
            c = int(pcwsreg["c"])
            xs1 = np.arange(1, c + 1)
            xs2 = np.arange(c, kmax + 1)
            ax.plot(xs1, pcwsreg["a1"] * xs1 + pcwsreg["b1"], linestyle="--", color="red")
            ax.plot(xs2, pcwsreg["a2"] * xs2 + pcwsreg["b2"], linestyle="--", color="red")
        if reg == 3:
            c1 = int(pcwsreg["c1"])
            c2 = int(pcwsreg["c2"])
            ax.plot(
                np.arange(1, c1 + 1),
                pcwsreg["a1"] * np.arange(1, c1 + 1) + pcwsreg["b1"],
                linestyle="--",
                color="blue",
            )
            ax.plot(
                np.arange(c1, c2 + 1),
                pcwsreg["a2"] * np.arange(c1, c2 + 1) + pcwsreg["b2"],
                linestyle="--",
                color="blue",
            )
            ax.plot(
                np.arange(c2, kmax + 1),
                pcwsreg["a3"] * np.arange(c2, kmax + 1) + pcwsreg["b3"],
                linestyle="--",
                color="blue",
            )
        plt.close(fig)

    k_opt = int(pcwsreg["K"]) if "K" in pcwsreg else int(pcwsreg["c"])
    z0 = z.copy()
    for k in range(kmax, k_opt - 1, -1):
        z0 = (combi_m[k] @ z0.T).T
    return {
        "numClusters.combi": k_opt,
        "z.combi": z0,
        "cluster.combi": _map(z0),
    }


def _pcws2_reg(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    c_len = len(x)
    ss_best = float("inf")
    c_best = a1_best = a2_best = b1_best = b2_best = None
    for c in range(2, c_len):
        x1, y1 = x[:c], y[:c]
        x2, y2 = x[c - 1 :], y[c - 1 :]
        a1 = np.sum((x1 - x1.mean()) * (y1 - y1.mean())) / np.sum((x1 - x1.mean()) ** 2)
        b1 = -a1 * x1.mean() + y1.mean()
        a2 = np.sum((x2 - x2.mean()) * (y2 - y2.mean())) / np.sum((x2 - x2.mean()) ** 2)
        b2 = -a2 * x2.mean() + y2.mean()
        ss = np.sum((a1 * x1 + b1 - y1) ** 2) + np.sum((a2 * x2 + b2 - y2) ** 2)
        if ss < ss_best:
            ss_best = ss
            c_best = c
            a1_best, a2_best, b1_best, b2_best = a1, a2, b1, b2
    return {
        "c": c_best,
        "a1": a1_best,
        "b1": b1_best,
        "a2": a2_best,
        "b2": b2_best,
    }


def _pcws3_reg(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    c_len = len(x)
    ss_best = float("inf")
    out: dict[str, Any] = {}
    for c1 in range(2, c_len - 1):
        for c2 in range(c1 + 1, c_len):
            x1, y1 = x[:c1], y[:c1]
            x2, y2 = x[c1 - 1 : c2], y[c1 - 1 : c2]
            x3, y3 = x[c2 - 1 :], y[c2 - 1 :]
            a1 = np.sum((x1 - x1.mean()) * (y1 - y1.mean())) / np.sum((x1 - x1.mean()) ** 2)
            b1 = -a1 * x1.mean() + y1.mean()
            a2 = np.sum((x2 - x2.mean()) * (y2 - y2.mean())) / np.sum((x2 - x2.mean()) ** 2)
            b2 = -a2 * x2.mean() + y2.mean()
            a3 = np.sum((x3 - x3.mean()) * (y3 - y3.mean())) / np.sum((x3 - x3.mean()) ** 2)
            b3 = -a3 * x3.mean() + y3.mean()
            ss = (
                np.sum((a1 * x1 + b1 - y1) ** 2)
                + np.sum((a2 * x2 + b2 - y2) ** 2)
                + np.sum((a3 * x3 + b3 - y3) ** 2)
            )
            if ss < ss_best:
                ss_best = ss
                out = {
                    "c1": c1,
                    "c2": c2,
                    "a1": a1,
                    "b1": b1,
                    "a2": a2,
                    "b2": b2,
                    "a3": a3,
                    "b3": b3,
                }
    return out


def _sum_xlog(x: np.ndarray) -> float:
    flat = np.asarray(x, dtype=float).ravel()
    return float(np.sum(np.where(flat == 0.0, 0.0, flat * np.log(flat))))


def _map(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    cl = np.empty(z.shape[0], dtype=float)
    for i in range(z.shape[0]):
        row_max = z[i, :].max()
        cols = np.flatnonzero(z[i, :] == row_max)
        cl[i] = cols[0] + 1
    return cl


def _field(obj: Any, name: str):
    if isinstance(obj, Mapping):
        return obj[name]
    return getattr(obj, name)
