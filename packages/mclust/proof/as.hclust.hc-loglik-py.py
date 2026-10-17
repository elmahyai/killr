"""Python side of the as.hclust.hc loglik proof. Same cases and log format as as.hclust.hc-loglik-r.R.

For each case the merge (column-major), height, order and cloglik of
``as_hclust_hc(..., what="loglik")`` are compared with R's values at 1e-8.
NA must match NA. The timed call is the whole loglik call: cloglik_hc (when
the case does not fix the cloglik) followed by as_hclust_hc. One untimed call,
then the median of 20 timed calls.
"""

import statistics  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

PROOF = Path(__file__).resolve().parent
ROOT = PROOF.parent
OUT = ROOT / "docs" / "output"
sys.path.insert(0, str(ROOT))

from mclust.as_hclust import as_hclust_hc  # noqa: E402
from mclust.plot_hc import cloglik_hc  # noqa: E402

# mvn's Python port warns on singular covariances, as R's Fortran does silently.
warnings.filterwarnings("ignore", category=RuntimeWarning)

TOL = 1e-8
KEYS = ["merge", "height", "order", "cloglik"]

# name, dataset, maxG, fixed cloglik name (None = computed by cloglik_hc)
CASES = [
    ("vvv_loglik", "vvv", None, None),
    ("eii_loglik", "eii", None, None),
    ("vvv_loglik_maxG5", "vvv", 5, None),
    ("eii_loglik_maxG3", "eii", 3, None),
    ("vvv_fixed_neg_early", "vvv", None, "neg_early"),
    ("vvv_fixed_neg_early_maxG2", "vvv", 2, "neg_early"),
    ("vvv_fixed_neg_late", "vvv", None, "neg_late"),
    ("vvv_fixed_neg_late_maxG4", "vvv", 4, "neg_late"),
    ("vvv_fixed_monotone", "vvv", None, "monotone"),
    ("vvv_fixed_monotone_maxG20", "vvv", 20, "monotone"),
]


def parse_values(text: str) -> np.ndarray:
    return np.array([np.nan if v == "NA" else float(v) for v in text.split()], dtype=float)


def load_dataset(name: str) -> dict:
    pairs = np.loadtxt(PROOF / f"as.hclust.hc-loglik_{name}_pairs.txt", ndmin=2)
    init = np.loadtxt(PROOF / f"as.hclust.hc-loglik_{name}_init.txt", dtype=int, ndmin=1)
    data = np.loadtxt(PROOF / f"as.hclust.hc-loglik_{name}_data.txt", ndmin=2)
    model, _what = (PROOF / f"as.hclust.hc-loglik_{name}_args.txt").read_text().split()
    return {"pairs": pairs, "initialPartition": init, "data": data,
            "modelName": model, "model": model}


def load_fixed(name: str) -> np.ndarray:
    return parse_values((PROOF / f"as.hclust.hc-loglik_fixed_{name}_cloglik.txt").read_text())


def r_cases() -> dict[str, dict[str, np.ndarray]]:
    cases: dict[str, dict[str, np.ndarray]] = {}
    current = None
    for line in (OUT / "as.hclust.hc-loglik-r.txt").read_text().splitlines():
        if not line:
            continue
        tag, _, rest = line.partition("\t")
        if tag == "CASE":
            current = rest
            cases[current] = {}
        else:
            cases[current][tag] = parse_values(rest)
    return cases


def r_times() -> dict[str, float]:
    times = {}
    for line in (OUT / "as.hclust.hc-loglik-r-time.txt").read_text().splitlines():
        if line.strip():
            name, ms = line.split("\t")
            times[name] = float(ms)
    return times


def compare(ref: np.ndarray, got: np.ndarray) -> float:
    """Largest absolute difference; NA must sit in the same places. inf if they differ."""
    if ref.shape != got.shape:
        return float("inf")
    na_ref, na_got = np.isnan(ref), np.isnan(got)
    if not np.array_equal(na_ref, na_got):
        return float("inf")
    keep = ~na_ref
    if not keep.any():
        return 0.0
    return float(np.max(np.abs(ref[keep] - got[keep])))


def run_case(name: str, dataset: str, maxG, fixed_name):
    x = load_dataset(dataset)
    fixed = None if fixed_name is None else load_fixed(fixed_name)

    def one():
        cll = fixed if fixed is not None else cloglik_hc(x)
        obj = dict(x)
        obj["cloglik"] = cll
        return as_hclust_hc(obj, what="loglik", maxG=maxG)

    return one


def main() -> None:
    reference = r_cases()
    rtimes = r_times()
    py_lines: list[str] = []
    summary: list[str] = []
    overall = True
    worst = 0.0
    for name, dataset, maxG, fixed_name in CASES:
        one = run_case(name, dataset, maxG, fixed_name)
        res = one()
        got = {
            "merge": np.asarray(res["merge"], dtype=float).ravel(order="F"),
            "height": np.asarray(res["height"], dtype=float),
            "order": np.asarray(res["order"], dtype=float),
            "cloglik": np.asarray(res["cloglik"], dtype=float),
        }
        diffs = {k: compare(reference[name][k], got[k]) for k in KEYS}
        matches = all(d <= TOL for d in diffs.values())
        max_abs = max(diffs[k] for k in ["merge", "height", "order"])
        overall = overall and matches
        worst = max(worst, max(diffs.values()))

        one()
        timed = []
        for _ in range(20):
            started = time.perf_counter()
            one()
            timed.append((time.perf_counter() - started) * 1000)
        t_ms = statistics.median(timed)
        r_ms = rtimes[name]
        speedup = r_ms / t_ms

        py_lines.append(f"CASE\t{name}")
        for k in KEYS:
            py_lines.append(k + "\t" + " ".join("NA" if np.isnan(v) else "%.17g" % v for v in got[k]))
        summary.append(
            f"{name}\tmatches={'yes' if matches else 'no'}\tmax_abs_diff={max_abs:.3g}"
            f"\tcloglik_max_abs_diff={diffs['cloglik']:.3g}\tr_ms={r_ms:.6g}"
            f"\ttranslated_ms={t_ms:.6g}\tspeedup={speedup:.4g}"
        )
        print(summary[-1])
        py_times = f"{name}\t{t_ms:.17g}"
        py_lines.append(f"TIME\t{py_times}")

    (OUT / "as.hclust.hc-loglik-py.txt").write_text("\n".join(py_lines) + "\n")
    (OUT / "as.hclust.hc-loglik.txt").write_text(
        "\n".join(["case\tmatches\tmax_abs_diff\tcloglik_max_abs_diff\tr_ms\ttranslated_ms\tspeedup"]
                  + summary) + f"\n\nall_match: {'yes' if overall else 'no'}\n"
        f"worst_abs_diff: {worst:.17g}\n")
    print(f"all_match {'yes' if overall else 'no'}")
    print(f"worst_abs_diff {worst:.17g}")


if __name__ == "__main__":
    main()
