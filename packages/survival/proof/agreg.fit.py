import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
sys.path = [entry for entry in sys.path if entry not in ("", _SCRIPT_DIR)]

from survival.agreg_fit import agreg_fit
from survival.control import coxph_control


def load_heart():
    path = Path(__file__).with_name("agfit4_heart.csv")
    raw = np.genfromtxt(path, delimiter=",", names=True)
    start = np.asarray(raw["start"], dtype=float)
    stop = np.asarray(raw["stop"], dtype=float)
    event = np.asarray(raw["event"], dtype=float)
    x = np.column_stack(
        [
            np.asarray(raw["age"], dtype=float),
            np.asarray(raw["year"], dtype=float),
            np.asarray(raw["surgery"], dtype=float),
            np.asarray(raw["transplant"], dtype=float),
        ]
    )
    return start, stop, event, x


def flat_fit(fit):
    vals = np.concatenate(
        [
            np.asarray(fit["coefficients"], dtype=float).reshape(-1),
            np.asarray(fit["first"], dtype=float).reshape(-1),
            np.ravel(np.asarray(fit["var"], dtype=float), order="F"),
            np.asarray(fit["loglik"], dtype=float).reshape(-1),
            np.array([fit["score"]], dtype=float),
            np.asarray(fit["info"], dtype=float).reshape(-1),
            np.array([fit["iter"]], dtype=float),
            np.asarray(fit["means"], dtype=float).reshape(-1),
            np.asarray(fit["residuals"], dtype=float).reshape(-1),
            np.asarray(fit["linear.predictors"], dtype=float).reshape(-1),
        ]
    )
    return ["NA" if v != v else f"{v:.17g}" for v in vals]


def flat_null(fit):
    vals = np.concatenate(
        [
            np.array([fit["loglik"]], dtype=float),
            np.asarray(fit["linear.predictors"], dtype=float).reshape(-1),
            np.asarray(fit["residuals"], dtype=float).reshape(-1),
        ]
    )
    return ["NA" if v != v else f"{v:.17g}" for v in vals]


def one(heart, synth, control):
    start, stop, event, x = heart
    s_start, s_stop, s_event, s_x, s_strata, s_weights, s_offset, s_init = synth
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        heart_fit = agreg_fit(
            x,
            np.column_stack([start, stop, event]),
            None,
            np.zeros(len(start)),
            np.zeros(x.shape[1]),
            control,
            np.ones(len(start)),
            "efron",
            None,
            True,
            (-1, 0, 1),
        )
        synth_fit = agreg_fit(
            s_x,
            np.column_stack([s_start, s_stop, s_event]),
            s_strata,
            s_offset,
            s_init,
            control,
            s_weights,
            "efron",
            None,
            True,
            (-1, 0, 1),
        )
        null_fit = agreg_fit(
            np.zeros((3, 0)),
            np.column_stack([np.zeros(3), np.array([4.0, 5.0, 6.0]), np.array([1.0, 0.0, 1.0])]),
            None,
            None,
            None,
            control,
            None,
            "breslow",
            None,
            True,
            (-1, 0, 1),
        )
    return flat_fit(heart_fit) + flat_fit(synth_fit) + flat_null(null_fit)


if __name__ == "__main__":
    heart = load_heart()
    synth = (
        np.array([0, 0.5, 1, 2, 6, 0, 0.2, 1, 0.4], dtype=float),
        np.array([5, 5, 10, 6, 7, 4, 4, 12, 2], dtype=float),
        np.array([1, 1, 0, 1, 0, 1, 1, 1, 0], dtype=float),
        np.column_stack(
            [
                np.array([0, 1, 1, 0, 1, 0, 1, 0, 1], dtype=float),
                np.array([1.2, 0.4, 2.0, -0.5, 3.0, 1.0, 0.0, 2.5, 0.5], dtype=float),
            ]
        ),
        np.array([1, 1, 1, 1, 1, 2, 2, 2, 2], dtype=np.int32),
        np.array([1, 1, 2, 1, 1, 1.5, 1, 1, 1], dtype=float),
        np.array([0, 0.2, 0, 0, 0, -0.1, 0, 0, 0.3], dtype=float),
        np.array([0.05, -0.1], dtype=float),
    )
    control = coxph_control(eps=1e-9, iter_max=20)
    value = one(heart, synth, control)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one(heart, synth, control)
        elapsed.append((time.perf_counter() - started) * 1000)
    print("\n".join(value))
    print("MS")
    print(f"{statistics.median(elapsed):.17g}")
