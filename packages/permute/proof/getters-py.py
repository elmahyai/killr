from pathlib import Path
import time
import numpy as np
import permute

root = Path(__file__).parents[1]
out = root / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

ctrl = permute.how(within=permute.Within(type="free"), nperm=5, observed=True)
calls = {
    "getRow": lambda: permute.getRow(ctrl),
    "getCol": lambda: permute.getCol(ctrl),
    "getDim": lambda: permute.getDim(ctrl),
    "getNperm": lambda: permute.getNperm(ctrl),
    "getMaxperm": lambda: permute.getMaxperm(ctrl),
    "getMinperm": lambda: permute.getMinperm(ctrl),
    "getComplete": lambda: permute.getComplete(ctrl),
    "getMake": lambda: permute.getMake(ctrl),
    "getObserved": lambda: permute.getObserved(ctrl),
    "getAllperms": lambda: permute.getAllperms(ctrl),
    "getControl": lambda: permute.getControl(ctrl),
}


def scalar(x):
    if x is None:
        return "None"
    if isinstance(x, (bool, np.bool_)):
        return str(bool(x)).lower()
    if isinstance(x, np.ndarray):
        if x.size == 0:
            return "[]"
        return ",".join(scalar(v) for v in x.ravel())
    if isinstance(x, (int, float, np.integer, np.floating)):
        return str(x)
    return str(x)


def canonical(x):
    if x is None or isinstance(x, (bool, int, float, str, np.generic, np.ndarray)):
        return scalar(x)
    if isinstance(x, permute.Within):
        fields = ("type", "constant", "mirror", "ncol", "nrow")
        return ";".join(f"{k}={canonical(getattr(x, k))}" for k in fields)
    if isinstance(x, permute.Plots):
        fields = ("strata", "type", "mirror", "ncol", "nrow")
        return ";".join(f"{k}={canonical(getattr(x, k))}" for k in fields)
    if hasattr(x, "within") and hasattr(x, "nperm"):
        fields = (("within", "within"), ("plots", "plots"), ("blocks", "blocks"),
                  ("nperm", "nperm"), ("complete", "complete"), ("maxperm", "maxperm"),
                  ("minperm", "minperm"), ("all.perms", "all_perms"),
                  ("make", "make"), ("observed", "observed"))
        return ";".join(f"{label}={canonical(getattr(x, attr))}"
                        for label, attr in fields)
    return scalar(x)


values = out / "getters-py-values.txt"
values.write_text("\n".join(f"{name}\t{canonical(fn())}" for name, fn in calls.items()) + "\n")

timing = {}
for name, fn in calls.items():
    fn()
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        for _ in range(1000):
            fn()
        samples.append((time.perf_counter() - start) * 1000 / 1000)
    timing[name] = float(np.median(samples))
(out / "getters-py-timing.tsv").write_text(
    "name\ttranslated_ms\n" + "\n".join(f"{k}\t{v:.12f}" for k, v in timing.items()) + "\n"
)

r_values = dict(line.rstrip("\n").split("\t", 1) for line in
                (out / "getters-r-values.txt").read_text().splitlines())
r_times = dict(line.split("\t") for line in
               (out / "getters-r-timing.tsv").read_text().splitlines()[1:])
report = ["function\tmatches\tmax_abs_diff\tr_ms\ttranslated_ms\tspeedup"]
for name, fn in calls.items():
    py_value = canonical(fn())
    matches = py_value == r_values[name]
    r_ms = float(r_times[name])
    py_ms = timing[name]
    report.append(f"{name}\t{'yes' if matches else 'no'}\t{0.0 if matches else 'NA'}"
                  f"\t{r_ms:.12f}\t{py_ms:.12f}\t{r_ms / py_ms:.12f}")
(out / "getters-proof.txt").write_text("\n".join(report) + "\n")
print("\n".join(report))
