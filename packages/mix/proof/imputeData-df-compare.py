"""Compare the R and Python outputs of imputeData-df-r.R and imputeData-df-py.py.

Reads the two output files in docs/output, checks every case within 1e-8 (factor code
columns exactly), and writes docs/output/imputeData-df-summary.txt. Speedup is the R
median time divided by the Python median time for the whole set of cases.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
TOL = 1e-8


def read(path):
    cases = []
    ms = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            _, name, nrow, ncol, cats = (line.split(" ", 4) + [""])[:5]
            cats = [int(c) for c in cats.split(",") if c]
            cases.append({"name": name, "nrow": int(nrow), "ncol": int(ncol), "cats": cats, "vals": []})
        elif cases and len(cases[-1]["vals"]) < cases[-1]["nrow"] * cases[-1]["ncol"]:
            cases[-1]["vals"].append(None if line == "NA" else float(line))
        else:
            ms = float(line)
    return cases, ms


r_cases, r_ms = read(OUT / "imputeData-df-r.txt")
p_cases, p_ms = read(OUT / "imputeData-df-py.txt")
assert [c["name"] for c in r_cases] == [c["name"] for c in p_cases], "case lists differ"

rows = []
all_match = True
for rc, pc in zip(r_cases, p_cases):
    n, m = rc["nrow"], rc["ncol"]
    cat_cols = set(rc["cats"])
    max_diff = 0.0
    numeric_ok = True
    factor_ok = True
    for k, (a, b) in enumerate(zip(rc["vals"], pc["vals"])):
        col = k // n  # column-major
        if a is None or b is None:
            if a is not None or b is not None:
                numeric_ok = False
            continue
        d = abs(a - b)
        max_diff = max(max_diff, d)
        if col in cat_cols:
            if a != b:
                factor_ok = False
        elif d > TOL:
            numeric_ok = False
    ok = numeric_ok and factor_ok
    all_match = all_match and ok
    rows.append((rc["name"], n, m, rc["cats"], max_diff, numeric_ok, factor_ok))

speed = r_ms / p_ms
lines = []
lines.append("imputeData data.frame and array proof (mclust 6.1.3, mix 1.0-13)")
lines.append("case, nrow, ncol, categorical columns, max_abs_diff, numeric within 1e-8, factor codes exact")
for name, n, m, cats, md, nok, fok in rows:
    lines.append("%s, %d, %d, %s, %.3g, %s, %s" % (
        name, n, m, ",".join(str(c) for c in cats) or "-", md,
        "yes" if nok else "no", "yes" if fok else "no"))
lines.append("all_match: %s" % ("yes" if all_match else "no"))
lines.append("max_abs_diff (all cases): %.3g" % max(r[4] for r in rows))
lines.append("r_ms: %.3f" % r_ms)
lines.append("translated_ms: %.3f" % p_ms)
lines.append("speedup (R time / Python time): %.4f" % speed)
text = "\n".join(lines) + "\n"
(OUT / "imputeData-df-summary.txt").write_text(text)
sys.stdout.write(text)
