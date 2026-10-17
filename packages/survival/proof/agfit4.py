"""Proof for the agfit4 and agmart3 kernels against survival::agreg.fit."""

import statistics
import sys
from pathlib import Path

import numpy as np

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
sys.path = [entry for entry in sys.path if entry not in ("", _SCRIPT_DIR)]

from agfit4 import agfit4, agmart3, kernel_ms

EPS = 1e-9
TOLER = float(np.finfo(np.float64).eps ** 0.75)
NOCENTER = np.array([-1.0, 0.0, 1.0])


def prepare(start, stop, event, strata, x, nocenter):
    start = np.asarray(start, dtype=np.float64)
    stop = np.asarray(stop, dtype=np.float64)
    event = np.asarray(event, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)
    nr = start.shape[0]
    if strata is None:
        y1 = start.copy()
        y2 = stop.copy()
        strata_i = np.zeros(nr, dtype=np.int32)
        use_strata = False
    else:
        strata_i = np.asarray(strata, dtype=np.int32)
        use_strata = True
        span = 1.0 + float(np.max(stop) - np.min(start))
        delta = strata_i.astype(np.float64) * span
        y1 = start + delta
        y2 = stop + delta
    occurred = event > 0
    dtime = np.unique(y2[occurred])
    indx1 = np.searchsorted(dtime, y1, side="right")
    indx2 = np.searchsorted(dtime, y2, side="right")
    ignore = indx1 == indx2
    nused = int(np.sum(~ignore))
    ignore_key = ignore.astype(np.int32)
    if use_strata:
        sort_end = np.lexsort((-stop, strata_i, ignore_key)).astype(np.int32)
        sort_start = np.lexsort((-start, strata_i, ignore_key)).astype(np.int32)
        strata_out = strata_i
    else:
        sort_end = np.lexsort((-stop, ignore_key)).astype(np.int32)
        sort_start = np.lexsort((-start, ignore_key)).astype(np.int32)
        strata_out = np.zeros(nr, dtype=np.int32)
    doscale = np.ones(x.shape[1], dtype=np.int32)
    for col in range(x.shape[1]):
        if np.all(np.isin(x[:, col], nocenter)):
            doscale[col] = 0
    return {
        "nused": nused,
        "y": np.column_stack([start, stop, event]),
        "x": x,
        "strata": strata_out,
        "sort_start": sort_start,
        "sort_end": sort_end,
        "doscale": doscale,
    }


def load_heart():
    path = Path(__file__).with_name("agfit4_heart.csv")
    raw = np.genfromtxt(path, delimiter=",", names=True)
    start = np.asarray(raw["start"], dtype=np.float64)
    stop = np.asarray(raw["stop"], dtype=np.float64)
    event = np.asarray(raw["event"], dtype=np.float64)
    x = np.column_stack(
        [
            np.asarray(raw["age"], dtype=np.float64),
            np.asarray(raw["year"], dtype=np.float64),
            np.asarray(raw["surgery"], dtype=np.float64),
            np.asarray(raw["transplant"], dtype=np.float64),
        ]
    )
    return start, stop, event, x


def synth():
    start = np.array([0, 0.5, 1, 2, 6, 0, 0.2, 1, 0.4], dtype=np.float64)
    stop = np.array([5, 5, 10, 6, 7, 4, 4, 12, 2], dtype=np.float64)
    event = np.array([1, 1, 0, 1, 0, 1, 1, 1, 0], dtype=np.float64)
    x = np.column_stack(
        [
            np.array([0, 1, 1, 0, 1, 0, 1, 0, 1], dtype=np.float64),
            np.array([1.2, 0.4, 2.0, -0.5, 3.0, 1.0, 0.0, 2.5, 0.5], dtype=np.float64),
        ]
    )
    strata = np.array([1, 1, 1, 1, 1, 2, 2, 2, 2], dtype=np.int32)
    weights = np.array([1, 1, 2, 1, 1, 1.5, 1, 1, 1], dtype=np.float64)
    offset = np.array([0, 0.2, 0, 0, 0, -0.1, 0, 0, 0.3], dtype=np.float64)
    init = np.array([0.05, -0.1], dtype=np.float64)
    return start, stop, event, x, strata, weights, offset, init


def score_of(x, coef, offset, doscale):
    means = x.mean(axis=0)
    means = np.where(doscale == 0, 0.0, means)
    lp = x @ coef + offset - float(np.dot(coef, means))
    limit = np.log(np.finfo(np.float64).max)
    if np.any(lp > limit):
        temp = lp + limit - (1.0 + np.max(lp))
        return np.exp(temp)
    return np.exp(lp)


def pack(case, weights, offset, init):
    prep = case["prep"]
    y = np.ascontiguousarray(prep["y"])
    x = np.ascontiguousarray(prep["x"])
    return {
        "nused": prep["nused"],
        "y": y,
        "x": x,
        "strata": np.ascontiguousarray(prep["strata"]),
        "weights": np.ascontiguousarray(weights, dtype=np.float64),
        "offset": np.ascontiguousarray(offset, dtype=np.float64),
        "init": np.ascontiguousarray(init, dtype=np.float64),
        "sort_start": np.ascontiguousarray(prep["sort_start"]),
        "sort_end": np.ascontiguousarray(prep["sort_end"]),
        "method": 1,
        "maxiter": 20,
        "eps": EPS,
        "toler_chol": TOLER,
        "doscale": np.ascontiguousarray(prep["doscale"]),
    }


def evaluate(packed):
    coef, u, imat, loglik, sctest, flag, iter_ = agfit4(
        packed["nused"],
        packed["y"],
        packed["x"],
        packed["strata"],
        packed["weights"],
        packed["offset"],
        packed["init"],
        packed["sort_start"],
        packed["sort_end"],
        packed["method"],
        packed["maxiter"],
        packed["eps"],
        packed["toler_chol"],
        packed["doscale"],
    )
    coef = np.asarray(coef, dtype=np.float64)
    score = score_of(packed["x"], coef, packed["offset"], packed["doscale"])
    resid = agmart3(
        packed["nused"],
        packed["y"],
        score,
        packed["weights"],
        packed["strata"],
        packed["sort_start"],
        packed["sort_end"],
        packed["method"],
    )
    imat = np.asarray(imat, dtype=np.float64)
    return [
        *(f"{value:.17g}" for value in coef),
        *(f"{value:.17g}" for value in np.asarray(u, dtype=np.float64)),
        *(f"{value:.17g}" for value in imat.ravel(order="F")),
        *(f"{value:.17g}" for value in np.asarray(loglik, dtype=np.float64)),
        f"{float(sctest):.17g}",
        *(f"{int(value):.17g}" for value in np.asarray(flag)),
        f"{int(iter_):.17g}",
        *(f"{value:.17g}" for value in np.asarray(resid, dtype=np.float64)),
    ], score


def kernel_milliseconds(packed, score):
    return kernel_ms(
        packed["nused"],
        packed["y"],
        packed["x"],
        packed["strata"],
        packed["weights"],
        packed["offset"],
        packed["init"],
        packed["sort_start"],
        packed["sort_end"],
        packed["method"],
        packed["maxiter"],
        packed["eps"],
        packed["toler_chol"],
        packed["doscale"],
        np.ascontiguousarray(score, dtype=np.float64),
    )


def main():
    start, stop, event, x = load_heart()
    heart = pack(
        {"prep": prepare(start, stop, event, None, x, NOCENTER)},
        np.ones(len(start)),
        np.zeros(len(start)),
        np.zeros(x.shape[1]),
    )
    s_start, s_stop, s_event, s_x, s_strata, s_weights, s_offset, s_init = synth()
    synthetic = pack(
        {"prep": prepare(s_start, s_stop, s_event, s_strata, s_x, NOCENTER)},
        s_weights,
        s_offset,
        s_init,
    )

    heart_lines, heart_score = evaluate(heart)
    synth_lines, synth_score = evaluate(synthetic)
    value = heart_lines + synth_lines

    elapsed = []
    for _ in range(20):
        elapsed.append(kernel_milliseconds(heart, heart_score) + kernel_milliseconds(synthetic, synth_score))

    print("\n".join(value))
    print("MS")
    print(f"{statistics.median(elapsed):.17g}")


if __name__ == "__main__":
    main()
