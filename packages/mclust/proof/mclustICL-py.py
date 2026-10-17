"""Proof: mclust.mclust_icl.mclustICL against R mclust 6.1.3 on the inputs of mclustICL-r.R.

Run from packages/mclust, after proof/mclustICL-r.R:
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/mclustICL-py.py

Compares, per case, the ICL matrix values (within 1e-8), and exactly the dimensions,
G, returnCodes, n, d, oneD, modelNames, criterion and class. Writes
docs/output/mclustICL-py.txt in the same layout as mclustICL-r.txt, and prints
the timing: one untimed call of all cases, then the median of 20 timed calls.
"""

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mclust.mclust_icl import mclustICL  # noqa: E402

PROOF = ROOT / "proof"
OUT = ROOT / "docs" / "output"
TOL = 1e-8

xfa = np.loadtxt(PROOF / "mclust_faithful.csv", delimiter=",")
ib = np.arange(1, 61)
xb = np.column_stack([((ib * 37) % 11) / 11 + 0.05 * ib / 60,
                      ((ib * 23) % 13) / 13 - 0.1 * ib / 60])
i3 = np.arange(1, 61)
g3 = (i3 - 1) % 3
x3 = np.column_stack([1.3 * np.cos(0.37 * i3) + 2.5 * g3,
                      0.9 * np.sin(0.53 * i3) + 0.8 * g3 - 0.5,
                      0.4 * np.cos(0.9 * i3) + 0.2 * np.sin(1.7 * i3)])
x1 = xb[:, 0]

MODELS6 = ["EII", "VII", "EEI", "VVI", "EEE", "VVV"]
partial = mclustICL(xb, G=[1, 2], modelNames=["EII"])


def one():
    return {
        "faithful_G1to4_4models": mclustICL(xfa, G=[1, 2, 3, 4],
                                            modelNames=["EII", "VVV", "EEE", "VEV"]),
        "oneD_default_G1to3": mclustICL(x1, G=[1, 2, 3]),
        "xb_G1to3_2models": mclustICL(xb, G=[1, 2, 3], modelNames=["EII", "VVV"]),
        "x3_G1to3_6models": mclustICL(x3, G=[1, 2, 3], modelNames=MODELS6),
        "oneD_G1_E_x1to4": mclustICL(np.array([1.0, 2.0, 3.0, 4.0]), G=[1], modelNames=["E"]),
        "xb_with_x": mclustICL(xb, G=[1, 2, 3], modelNames=["EII", "VVV"], x=partial),
    }


def fmt(v):
    if v is None:
        return "NA"
    v = float(v)
    return "NA" if math.isnan(v) else "%.17g" % v


def case_lines(name, o):
    vals = np.asarray(o["values"], dtype=float)
    codes = np.asarray(o["returnCodes"], dtype=float)
    n, d = o["n"], o["d"]
    one_d = bool(o["oneD"])
    return [
        f"CASE\t{name}",
        "\t".join([name, "values", str(vals.shape[0]), str(vals.shape[1])]),
        "\t".join([name, "valuesdata"] + [fmt(v) for v in vals.ravel(order="F")]),
        "\t".join([name, "G"] + [fmt(v) for v in o["G"]]),
        "\t".join([name, "returnCodes"] + [fmt(v) for v in codes.ravel(order="F")]),
        "\t".join([name, "n", fmt(n), "d", fmt(d), "oneD", fmt(float(one_d))]),
        "\t".join([name, "modelNames"] + list(o["modelNames"])),
        "\t".join([name, "criterion", o["criterion"], o["class"]]),
    ]


def read_r(path):
    cases = {}
    current = None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if parts[0] == "CASE":
            current = parts[1]
            cases[current] = {}
            continue
        if parts[0] == "time_ms":
            cases["__time__"] = float(parts[1])
            continue
        cases[current][parts[1]] = parts[2:]
    return cases


def as_num(tok):
    return float("nan") if tok == "NA" else float(tok)


def compare(ref, py_lines_by_case):
    """Return per-case match, max abs diff of values, and the first mismatch text."""
    report = {}
    for name, fields in py_lines_by_case.items():
        r = ref[name]
        worst = 0.0
        ok = True
        why = ""
        # values dims
        if [int(v) for v in r["values"]] != [int(v) for v in fields["values"][:2]]:
            ok, why = False, "dims"
        ra = np.array([as_num(t) for t in r["valuesdata"]])
        pa = np.array([as_num(t) for t in fields["valuesdata"]])
        if ra.shape != pa.shape or not np.array_equal(np.isnan(ra), np.isnan(pa)):
            ok, why = False, "NA pattern or length"
        else:
            m = ~np.isnan(ra)
            worst = float(np.max(np.abs(ra[m] - pa[m]))) if m.any() else 0.0
            if worst > TOL:
                ok, why = False, "values"
        for key in ("G", "returnCodes", "n", "modelNames", "criterion"):
            if key == "n":
                # n, d, oneD are one record in R's output
                if r["n"] != fields["n"]:
                    ok, why = False, "n/d/oneD"
                continue
            if key in ("G", "returnCodes"):
                rv = [as_num(t) for t in r[key]]
                pv = [as_num(t) for t in fields[key]]
                if len(rv) != len(pv) or any(abs(a - b) > TOL for a, b in zip(rv, pv)):
                    ok, why = False, key
            else:
                if r[key] != fields[key]:
                    ok, why = False, key
        report[name] = (ok, worst, why)
    return report


def main():
    res = one()
    lines = []
    py_fields = {}
    for name, o in res.items():
        block = case_lines(name, o)
        lines.extend(block)
        fields = {}
        for line in block[1:]:
            parts = line.split("\t")
            fields[parts[1]] = parts[2:]
        py_fields[name] = fields

    ref = read_r(OUT / "mclustICL-r.txt")
    report = compare(ref, py_fields)

    timed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        timed.append((time.perf_counter() - started) * 1000.0)
    t_ms = statistics.median(timed)
    lines.append(f"time_ms\t{'%.17g' % t_ms}")
    (OUT / "mclustICL-py.txt").write_text("\n".join(lines) + "\n")

    overall = all(v[0] for v in report.values())
    worst = max(v[1] for v in report.values())
    for name, (ok, diff, why) in report.items():
        print(f"case {name}: matches {'yes' if ok else 'no'} max_abs_diff {diff:.3g}"
              + ("" if ok else f" ({why})"))
    print(f"matches {'yes' if overall else 'no'}")
    print(f"max_abs_diff {worst:.17g}")
    r_ms = ref["__time__"]
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {t_ms:.17g}")
    print(f"speedup {r_ms / t_ms:.17g}")


if __name__ == "__main__":
    main()
