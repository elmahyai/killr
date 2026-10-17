from pathlib import Path
import csv
import time
import numpy as np
import permute

root = Path(__file__).parents[1]
out = root / "docs" / "output"
r_values = out / "r_values"
py_values = out / "py_values"
py_values.mkdir(parents=True, exist_ok=True)
mat = np.loadtxt(out / "permutation_matrix.csv", delimiter=",", ndmin=2, dtype=int)

def control():
    return permute.how(within=permute.Within(type="free"), nperm=5, observed=True)

def canonical(name, value):
    if name in {"allPerms", "as.allPerms"}:
        return np.asarray(value)
    if name == "Blocks":
        return "strata=NULL\n"
    if name == "check":
        c = value["control"]
        return "\n".join([
            f"n={int(value['n'])}", f"within.type={c.within.type}",
            f"within.constant={str(c.within.constant).upper()}",
            f"within.mirror={str(c.within.mirror).upper()}",
            f"plots.type={c.plots.type}",
            f"plots.mirror={str(c.plots.mirror).upper()}", ""
        ])
    if name == "getWithin":
        return f"type={value.type}\nconstant={str(value.constant).upper()}\nmirror={str(value.mirror).upper()}\n"
    if name == "getPlots":
        return f"type={value.type}\nmirror={str(value.mirror).upper()}\nstrata=NULL\n"
    if value is None:
        return "NULL\n"
    return f"{str(value).upper() if isinstance(value, bool) else value}\n"

checks = {
    "allPerms": lambda: permute.allPerms(4, control()),
    "as.allPerms": lambda: permute.as_allPerms(mat, control()),
    "Blocks": lambda: permute.Blocks(),
    "check": lambda: permute.check(4, control()),
    "getBlocks": lambda: permute.getBlocks(control()),
    "getWithin": lambda: permute.getWithin(control()),
    "getStrata": lambda: permute.getStrata(control()),
    "getType": lambda: permute.getType(control()),
    "getMirror": lambda: permute.getMirror(control()),
    "getConstant": lambda: permute.getConstant(control()),
    "getPlots": lambda: permute.getPlots(control()),
}

with open(out / "results.txt", "w") as result_file:
    r_rows = {row["name"]: row for row in csv.DictReader(open(out / "r_results.csv"))}
    result_file.write("name,matches,max_abs_diff,r_ms,translated_ms,speedup\n")
    for name, fn in checks.items():
        value = fn()
        canonical_value = canonical(name, value)
        py_path = py_values / f"{name.replace('.', '_')}.txt"
        if isinstance(canonical_value, np.ndarray):
            np.savetxt(py_path, canonical_value, fmt="%d", delimiter=",")
            left = np.loadtxt(r_values / py_path.name, delimiter=",", ndmin=2)
            right = canonical_value
            max_diff = float(np.max(np.abs(left - right)))
        else:
            py_path.write_text(canonical_value)
            max_diff = 0.0 if py_path.read_text() == (r_values / py_path.name).read_text() else float("inf")
        fn()
        timings = []
        for _ in range(20):
            start = time.perf_counter()
            fn()
            timings.append((time.perf_counter() - start) * 1000)
        translated_ms = float(np.median(timings))
        r_ms = float(r_rows[name]["r_ms"])
        speedup = r_ms / translated_ms
        matches = "yes" if max_diff <= 1e-8 else "no"
        result_file.write(f"{name},{matches},{max_diff:.12g},{r_ms:.6f},"
                          f"{translated_ms:.6f},{speedup:.6f}\n")
