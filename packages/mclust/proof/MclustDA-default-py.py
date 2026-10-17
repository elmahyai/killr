"""Proof: Python MclustDA with the default modelType (MclustDA) on the fixed inputs of
MclustDA-default-r.R. Run from packages/mclust:

    python3 proof/MclustDA-default-py.py

Writes docs/output/MclustDA-default-python.txt in the same record layout as the R
script (key, type, values; the last record is time_ms, the median of 20 timed
calls of fit + predict, in milliseconds). Then compares with
docs/output/MclustDA-default-r.txt and prints the comparison summary.
"""

from __future__ import annotations

import math
import re
import statistics
import sys
import time
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

from mclust.mclustda_fit import MclustDA  # noqa: E402
from mclust.predict_mclust_da import predict_mclust_da  # noqa: E402

TOL = 1e-8


def make_inputs():
    i_a = np.arange(1, 91)
    g_a = (i_a - 1) // 30
    xa = np.column_stack([
        ((i_a * 37) % 11) / 11 + 2.5 * g_a + 0.05 * i_a / 90,
        ((i_a * 23) % 13) / 13 + 1.5 * g_a + 0.4 * (((i_a * 37) % 11) / 11) + 0.01 * i_a,
    ])
    ya = np.array(["abc"[g] for g in g_a], dtype=object)

    i_b = np.arange(1, 61)
    g_b = (i_b - 1) // 30
    xb = (np.sin(0.37 * i_b) + 2.5 * g_b + 0.05 * i_b / 60).reshape(-1, 1)
    yb = np.array(["hi" if g == 0 else "lo" for g in g_b], dtype=object)

    def mk3(i, g):
        n = len(i)
        x = np.zeros((n, 3))
        for j in range(1, 4):
            x[:, j - 1] = (np.sin(0.37 * i + 1.3 * j) + 0.4 * np.cos(0.11 * i * j)
                           + 1.5 * g * (j / 3) + 0.05 * i / n * j)
        return x

    i_c = np.arange(1, 121)
    g_c = (i_c - 1) // 60
    xc = mk3(i_c, g_c)
    yc = np.array(["uv"[g] for g in g_c], dtype=object)

    i_d = np.arange(1, 84)
    g_d = np.where(i_d <= 40, 0, np.where(i_d <= 80, 1, 2))
    xd = mk3(i_d, g_d)
    yd = np.array(["pqr"[g] for g in g_d], dtype=object)

    return {
        "A": (xa, ya),
        "B": (xb, yb),
        "C": (xc, yc),
        "D": (xd, yd),
    }


def fit_case(x, y):
    fit = MclustDA(x, y, verbose=False)
    levels = sorted(set(y.tolist()))
    train_pred = predict_mclust_da(fit, newdata=x)
    nd = x[::3] + 0.07
    nd_pred = predict_mclust_da(fit, newdata=nd)
    return fit, levels, train_pred, nd_pred


def one(inputs):
    return {case: fit_case(*inputs[case]) for case in inputs}


def num(x):
    a = np.asarray(x, dtype=float).ravel(order="F")
    return " ".join("NA" if (v is None or math.isnan(v)) else "%.17g" % v for v in a)


def num_rec(key, x):
    return f"{key}\tn\t{num(x)}"


def str_rec(key, x):
    return f"{key}\ts\t{' '.join(str(v) for v in np.atleast_1d(x))}"


def emit_matrix(key, x):
    if x is None:
        return []
    a = np.asarray(x, dtype=float)
    return [num_rec(f"{key}|dim", np.array(a.shape, dtype=float)), num_rec(key, a)]


def emit_pred(prefix, pred, levels):
    cls = [levels.index(str(c)) + 1 for c in pred["classification"]]
    return [num_rec(f"{prefix}|classification", np.array(cls, dtype=float)),
            *emit_matrix(f"{prefix}|z", pred["z"])]


def get(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def emit_fit(case, fit, levels, train_pred, nd_pred):
    def p(k):
        return f"{case}|{k}"

    prop = np.asarray(list(fit["prop"].values()), dtype=float)
    out = [
        num_rec(p("n"), np.array(fit["n"], dtype=float)),
        num_rec(p("d"), np.array(fit["d"], dtype=float)),
        num_rec(p("prop"), prop),
        num_rec(p("loglik"), np.array(fit["loglik"], dtype=float)),
        num_rec(p("df"), np.array(fit["df"], dtype=float)),
        num_rec(p("bic"), np.array(fit["bic"], dtype=float)),
        str_rec(p("type"), fit["type"]),
        str_rec(p("labels"), levels),
    ]
    out += emit_pred(p("train"), train_pred, levels)
    out += emit_pred(p("newdata"), nd_pred, levels)
    for l, label in enumerate(levels, start=1):
        m = fit["models"][label]
        q = lambda k, l=l: f"{case}|class{l}|{k}"  # noqa: E731
        out += [
            str_rec(q("modelName"), m["modelName"]),
            num_rec(q("G"), np.array(m["G"], dtype=float)),
            num_rec(q("n"), np.array(m["n"], dtype=float)),
            num_rec(q("loglik"), np.array(m["loglik"], dtype=float)),
            num_rec(q("observations"), np.asarray(m["observations"], dtype=float)),
            num_rec(q("classification"), np.asarray(m["classification"], dtype=float)),
            *emit_matrix(q("z"), m.get("z")),
            num_rec(q("uncertainty"), np.asarray(get(m, "uncertainty") if get(m, "uncertainty") is not None else [], dtype=float)),
        ]
        bic = m["BIC"]
        values = np.asarray(get(bic, "values"), dtype=float)
        out += emit_matrix(q("BIC"), values)
        out += [
            str_rec(q("BIC|modelNames"), get(bic, "modelNames")),
            str_rec(q("BIC|G"), get(bic, "G")),
        ]
        out += emit_matrix(q("mean"), m["parameters"]["mean"])
        out.append(num_rec(q("pro"), np.asarray(m["parameters"]["pro"], dtype=float)))
        v = m["parameters"]["variance"]
        for nm in ["sigma", "sigmasq", "scale", "shape", "orientation", "Sigma",
                   "cholSigma", "cholsigma"]:
            if v.get(nm) is not None:
                out += emit_matrix(q(f"variance|{nm}"), v[nm])
    return out


def build_lines(results, levels_by_case):
    lines = []
    for case, (fit, levels, train_pred, nd_pred) in results.items():
        lines += emit_fit(case, fit, levels, train_pred, nd_pred)
    return lines


def parse(path):
    recs = {}
    for line in Path(path).read_text().splitlines():
        key, typ, rest = line.split("\t", 2)
        if typ == "n":
            vals = [float("nan") if t == "NA" else float(t) for t in rest.split()] if rest.strip() else []
            recs[key] = ("n", np.array(vals, dtype=float))
        else:
            recs[key] = ("s", rest)
    return recs


def compare(r_path, py_lines):
    r = parse(r_path)
    py = {}
    for line in py_lines:
        key, typ, rest = line.split("\t", 2)
        if typ == "n":
            vals = [float("nan") if t == "NA" else float(t) for t in rest.split()] if rest.strip() else []
            py[key] = ("n", np.array(vals, dtype=float))
        else:
            py[key] = ("s", rest)
    keys = sorted(set(r) | set(py))
    worst = 0.0
    mismatches = []
    skipped_dims = 0
    per_case: dict[str, float] = {}
    for key in keys:
        if key.endswith("|time_ms") or key == "time_ms":
            continue
        if key not in r or key not in py:
            mismatches.append(f"missing on one side: {key}")
            continue
        tr, vr = r[key]
        tp, vp = py[key]
        if key.endswith("|dim") and tr == "n" and vr.size == 0:
            # R stores this value as a plain vector (no dim attribute); the Python
            # side keeps it as a 1-by-G or G-by-1 array. The values are compared
            # below through the flattened record, so only the dim record is skipped.
            skipped_dims += 1
            continue
        if tr != tp:
            mismatches.append(f"type differs: {key}")
            continue
        if tr == "s":
            if vr != vp:
                mismatches.append(f"string differs: {key}: R={vr!r} py={vp!r}")
            continue
        if vr.shape != vp.shape:
            mismatches.append(f"shape differs: {key}: R={vr.shape} py={vp.shape}")
            continue
        both_nan = np.isnan(vr) & np.isnan(vp)
        one_nan = np.isnan(vr) ^ np.isnan(vp)
        if one_nan.any():
            mismatches.append(f"NA pattern differs: {key}")
        # Values are compared wherever both sides are finite; NA-pattern
        # differences are reported above and are not hidden by this maximum.
        both_finite = ~np.isnan(vr) & ~np.isnan(vp)
        if both_finite.any():
            diff = np.abs(vr[both_finite] - vp[both_finite])
            m = float(np.max(diff))
            worst = max(worst, m)
            case = key.split("|")[0]
            per_case[case] = max(per_case.get(case, 0.0), m)
            if m > TOL:
                mismatches.append(f"value differs: {key}: max={m:.3g}")
    return worst, mismatches, len(keys), skipped_dims, per_case


def main():
    inputs = make_inputs()
    results = one(inputs)
    lines = build_lines(results, None)

    elapsed = []
    for _ in range(20):
        t0 = time.perf_counter()
        one(inputs)
        elapsed.append((time.perf_counter() - t0) * 1000)
    median_ms = statistics.median(elapsed)

    # Per case: one untimed call, then the median of 20 timed calls of fit + predict.
    case_ms: dict[str, float] = {}
    for case, args in inputs.items():
        fit_case(*args)
        times = []
        for _ in range(20):
            t0 = time.perf_counter()
            fit_case(*args)
            times.append((time.perf_counter() - t0) * 1000)
        case_ms[case] = statistics.median(times)
        lines.append(f"{case}|time_ms\tn\t{case_ms[case]:.17g}")
    lines.append(f"time_ms\tn\t{median_ms:.17g}")

    out_dir = PKG / "docs" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "MclustDA-default-python.txt").write_text("\n".join(lines) + "\n")

    r_path = out_dir / "MclustDA-default-r.txt"
    report = []
    if r_path.exists():
        worst, mismatches, nkeys, skipped, per_case = compare(r_path, lines)
        r = parse(r_path)
        r_time = r["time_ms"][1][0]
        bad_cases = {c for m in mismatches for c in re.findall(r"(?<![A-Za-z])([A-D])\|", m)}
        report.append(f"keys compared: {nkeys} (R-vector dim records skipped: {skipped})")
        report.append(f"max_abs_diff: {worst:.3g}")
        report.append("max_abs_diff by case: " + ", ".join(
            f"{c}={v:.3g}" for c, v in sorted(per_case.items())))
        report.append(f"matches: {'yes' if not mismatches and worst <= TOL else 'no'}")
        for c in sorted(case_ms):
            r_c = r[f"{c}|time_ms"][1][0]
            ok = c not in bad_cases and per_case.get(c, 0.0) <= TOL
            report.append(
                f"case {c}: matches={'yes' if ok else 'no'} "
                f"max_abs_diff={per_case.get(c, 0.0):.3g} r_ms={r_c:.6g} "
                f"translated_ms={case_ms[c]:.6g} speedup={r_c / case_ms[c]:.6g}")
        report.extend("  " + m for m in mismatches)
        report.append(f"r_ms: {r_time:.6g}")
    report.append(f"translated_ms: {median_ms:.6g}")
    if r_path.exists():
        report.append(f"speedup: {r_time / median_ms:.6g}")
    text = "\n".join(report) + "\n"
    (out_dir / "MclustDA-default-compare.txt").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
