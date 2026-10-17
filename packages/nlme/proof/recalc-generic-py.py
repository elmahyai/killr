"""Generic recalc.corStruct proof: a user-defined correlation class, Python against R 3.1-171.

Runs proof/recalc-generic-r.R, runs the same two cases here, writes both outputs under
docs/output/, and prints the comparison (matches, max_abs_diff, r_ms, translated_ms, speedup).
The user classes supply corMatrix (and, for corToyUser, a recalc method); recalc() reaches
recalc_cor_struct the way R's UseMethod reaches recalc.corStruct.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
from coverage_common import ROOT, load_nlme  # noqa: E402

load_nlme()
from nlme.corstruct import initialize_cor_struct  # noqa: E402
from nlme.glsapvar import ConLin  # noqa: E402
from nlme.recalc import recalc, recalc_cor_struct  # noqa: E402

OUT = ROOT / "docs" / "output"
TOL = 1e-8

DAT_SUB = {"Subject": ["a", "a", "a", "a", "b", "b", "b"], "t": [1, 2, 3, 4, 1, 2, 4]}


class CorToy:
    """User-defined correlation class: exp(-theta * (t_i - t_j)^2). Supplies corMatrix only."""

    def __init__(self, value: float, form: str) -> None:
        self.value = np.asarray([value], dtype=np.float64)
        self.formula = form
        self.groups = None
        self.dim = None
        self.covariate = None

    def corMatrix(self, covariate=None, corr=True, **_ignored):
        if not corr:
            # R: NextMethod() to corMatrix.corStruct, which builds the transpose inverse factor
            # from the correlation blocks. Only the logLik path (logDet) reaches this.
            raise NotImplementedError("corr = FALSE is built by the generic path, not here")
        theta = float(self.value[0])
        cov = self.covariate if covariate is None else covariate
        blocks = cov.values() if isinstance(cov, dict) else cov
        return [np.exp(-theta * np.subtract.outer(np.asarray(t, dtype=np.float64),
                                                  np.asarray(t, dtype=np.float64)) ** 2)
                for t in blocks]


class CorToyUser(CorToy):
    """Same class with a user recalc method; it delegates to the generic path (NextMethod)."""

    def recalc(self, conLin):
        return recalc_cor_struct(self, conLin)


def con(logLik: float = 0.5) -> ConLin:
    return ConLin(
        Xy=np.arange(1, 15, dtype=np.float64).reshape(7, 2, order="F"),
        dims={"N": 7, "p": 2},
        logLik=logLik,
    )


def pair(obj, conlin):
    return (obj, conlin)


CASES = {
    "corToy": lambda: [
        pair(initialize_cor_struct(CorToy(0.4, "~ t | Subject"), DAT_SUB), con()),
        pair(initialize_cor_struct(CorToy(0.15, "~ t | Subject"), DAT_SUB), con()),
    ],
    "corToyUser": lambda: [
        pair(initialize_cor_struct(CorToyUser(0.25, "~ t | Subject"), DAT_SUB), con()),
    ],
}


def run_pairs(pairs) -> np.ndarray:
    parts = []
    for obj, conlin in pairs:
        result = recalc(obj, conlin)
        parts.append(np.ravel(np.asarray(result.Xy, dtype=np.float64), order="F"))
        parts.append(np.asarray([float(result.logLik)], dtype=np.float64))
    return np.concatenate(parts)


def timed(pairs) -> dict:
    """One untimed recalc, then the median of 20 timed recalc calls (milliseconds)."""
    value = run_pairs(pairs)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        run_pairs(pairs)
        elapsed.append((time.perf_counter() - started) * 1000)
    return {"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}


def python_results() -> dict:
    return {name: timed(setup()) for name, setup in CASES.items()}


def r_results() -> dict:
    command = ["Rscript", str(PROOF / "recalc-generic-r.R")]
    done = subprocess.run(command, capture_output=True, text=True, check=True)
    # R may print tracing messages before the JSON line; the JSON is the last line.
    json_lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
    return json.loads(json_lines[-1])


def compare(r_entry: dict, py_entry: dict) -> tuple[str, float, float, float]:
    r_vals = np.asarray(r_entry["value"], dtype=np.float64)
    py_vals = np.asarray(py_entry["value"], dtype=np.float64)
    if r_vals.shape != py_vals.shape:
        return "no", float("nan"), r_entry["median_ms"], py_entry["median_ms"]
    max_diff = float(np.max(np.abs(r_vals - py_vals)))
    ok = "yes" if max_diff <= TOL else "no"
    return ok, max_diff, float(r_entry["median_ms"]), float(py_entry["median_ms"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    r_out = r_results()
    py_out = python_results()
    (OUT / "recalc-generic-r.txt").write_text(json.dumps(r_out) + "\n")
    (OUT / "recalc-generic-python.txt").write_text(json.dumps(py_out) + "\n")
    lines = [
        "class | matches (<=1e-8) | max_abs_diff | r_ms | translated_ms | speedup (R/Python)",
    ]
    for name in CASES:
        ok, diff, r_ms, py_ms = compare(r_out[name], py_out[name])
        speed = r_ms / py_ms if py_ms > 0 else float("inf")
        lines.append(f"{name} | {ok} | {diff:.3g} | {r_ms:.4g} | {py_ms:.4g} | {speed:.3g}")
    summary = "\n".join(lines) + "\n"
    (OUT / "recalc-generic-compare.txt").write_text(summary)
    print(summary, end="")


if __name__ == "__main__":
    main()
