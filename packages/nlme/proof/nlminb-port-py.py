"""nlminb_port (crates/nlminb_port) against R 4.5.0 nlminb, no gradient.

Reads R's output from docs/output/nlminb-port-r.txt (made by nlminb-port-r.R),
runs the same six problems through the crate, and writes the comparison to
docs/output/nlminb-port-python.txt. Each problem: one untimed call, then the
median of 20 timed calls with time.perf_counter().
"""

import json
import math
import statistics
import time
from pathlib import Path

from nlminb_port import nlminb_port

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
R_JSON = OUT / "nlminb-port-r.txt"
PY_TXT = OUT / "nlminb-port-python.txt"
MAX_TOL = 1e-8

# The objectives mirror nlminb-port-r.R operation for operation, so the same
# doubles reach the driver. Sums are explicit double accumulations.


def rosen2(x):
    t = x[1] - x[0] * x[0]
    return 100.0 * (t * t) + (1.0 - x[0]) * (1.0 - x[0])


def rosenN(x):
    n = len(x)
    s = 0.0
    for i in range(n - 1):
        t = x[i + 1] - x[i] * x[i]
        s = s + (100.0 * (t * t) + (1.0 - x[i]) * (1.0 - x[i]))
    return s


TT = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
YY = [
    3.3,
    2.505550059402673,
    1.9156561772322491,
    1.5252110893106732,
    1.319564695520797,
    1.1622928214702366,
    1.0057986425957248,
    0.9334810431959338,
    0.9276803643916104,
    0.8802115233121498,
]


def nls3(p):
    a = p[0]
    b = p[1]
    cc = p[2]
    s = 0.0
    for i in range(10):
        r = YY[i] - (a * math.exp((-b) * TT[i]) + cc)
        s = s + r * r
    return s


def bquad(x):
    d1 = x[0] - 3.0
    d2 = x[1] - 2.0
    return d1 * d1 + d2 * d2


PROBLEMS = [
    dict(name="rosenbrock_2d", fn=rosen2, start=[-1.2, 1.0], lower=-math.inf, upper=math.inf, control={}),
    dict(name="nls_3par", fn=nls3, start=[1.0, 0.1, 0.5], lower=-math.inf, upper=math.inf, control={}),
    dict(name="bounded_quadratic_on_bound", fn=bquad, start=[0.5, 0.5], lower=[0.0, 0.0], upper=[2.0, 5.0], control={}),
    dict(name="rosenbrock_5d", fn=rosenN, start=[-1.2, 1.0, -1.2, 1.0, -1.2], lower=-math.inf, upper=math.inf, control={}),
    dict(name="rosenbrock_5d_upper_bound", fn=rosenN, start=[-1.2, 0.8, -1.2, 0.8, -1.2], lower=-2.0, upper=0.9, control={}),
    dict(
        name="rosenbrock_2d_control",
        fn=rosen2,
        start=[-1.2, 1.0],
        lower=-math.inf,
        upper=math.inf,
        control={"eval.max": 300, "iter.max": 150, "rel.tol": 1e-12, "x.tol": 1.5e-10},
    ),
]


def run(problem):
    return nlminb_port(
        problem["fn"],
        problem["start"],
        lower=problem["lower"],
        upper=problem["upper"],
        control=problem["control"],
    )


def main():
    r_results = {p["name"]: p for p in json.loads(R_JSON.read_text())["problems"]}
    lines = []
    lines.append("nlminb_port (Rust crate on portsrc.f) against R 4.5.0 stats::nlminb, no gradient")
    lines.append("tolerance: max abs diff <= %g on par and objective; counts and codes exact" % MAX_TOL)
    lines.append("")
    all_ok = True
    for problem in PROBLEMS:
        name = problem["name"]
        r = r_results[name]
        value = run(problem)  # untimed
        elapsed = []
        for _ in range(20):
            started = time.perf_counter()
            run(problem)
            elapsed.append((time.perf_counter() - started) * 1000.0)
        py_ms = statistics.median(elapsed)
        r_ms = r["median_ms"]

        par_diff = max(abs(a - b) for a, b in zip(value["par"], r["par"]))
        obj_diff = abs(value["objective"] - r["objective"])
        counts_equal = (
            value["iterations"] == r["iterations"]
            and value["evaluations"]["function"] == r["evaluations_function"]
            and value["evaluations"]["gradient"] == r["evaluations_gradient"]
        )
        code_equal = value["convergence"] == r["convergence"] and value["message"] == r["message"]
        matches = par_diff <= MAX_TOL and obj_diff <= MAX_TOL and counts_equal and code_equal
        all_ok = all_ok and matches

        lines.append("problem: %s" % name)
        lines.append("  matches: %s" % ("yes" if matches else "no"))
        lines.append("  max_abs_diff_par: %.3e" % par_diff)
        lines.append("  max_abs_diff_objective: %.3e" % obj_diff)
        lines.append("  convergence: R %d, python %d (equal: %s)" % (r["convergence"], value["convergence"], "yes" if value["convergence"] == r["convergence"] else "no"))
        lines.append("  message: R '%s' | python '%s'" % (r["message"], value["message"]))
        lines.append(
            "  iterations: R %d, python %d (equal: %s)"
            % (r["iterations"], value["iterations"], "yes" if value["iterations"] == r["iterations"] else "no")
        )
        lines.append(
            "  evaluations_function: R %d, python %d (equal: %s)"
            % (r["evaluations_function"], value["evaluations"]["function"], "yes" if value["evaluations"]["function"] == r["evaluations_function"] else "no")
        )
        lines.append(
            "  evaluations_gradient: R %d, python %d (equal: %s)"
            % (r["evaluations_gradient"], value["evaluations"]["gradient"], "yes" if value["evaluations"]["gradient"] == r["evaluations_gradient"] else "no")
        )
        lines.append("  r_ms: %.6f" % r_ms)
        lines.append("  translated_ms: %.6f" % py_ms)
        lines.append("  speedup: %.3f" % (r_ms / py_ms))
        lines.append("")

    lines.append("all problems match: %s" % ("yes" if all_ok else "no"))
    PY_TXT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
