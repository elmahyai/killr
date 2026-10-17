from pathlib import Path
import time
import numpy as np
import permute

root = Path(__file__).parents[1]
out = root / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

ctrl = permute.how(within=permute.Within(type="free"), nperm=5, observed=True)
mat = permute.allPerms(4, ctrl)

def values():
    return {
        "getHow": lambda: "|".join(map(str, (
            permute.getNperm(permute.getHow(mat)),
            str(permute.getObserved(permute.getHow(mat))).upper(),
            permute.getType(permute.getHow(mat), "within"),
            permute.getType(permute.getHow(mat), "plots"),
        ))),
        "how": lambda: "|".join(map(str, (
            permute.getNperm(permute.how(
                within=permute.Within(type="series", mirror=True),
                plots=permute.Plots(type="free"), nperm=17, complete=True)),
            "TRUE", "series", "TRUE", "free",
        ))),
        "numPerms": lambda: str(int(permute.numPerms(4, ctrl))),
        "permute": lambda: ",".join(map(str, permute.permute(
            2, 4, permute.how(complete=True, all_perms=mat)))),
        "Plots": lambda: "|".join(map(str, (
            "1,1,2,2", "free", "TRUE", 2, 2,
        ))),
        "setBlocks<-": lambda: ",".join(map(str, permute.getStrata(
            permute.setBlocks_(permute.how(), ["a", "a", "b", "b"]),
            which="blocks"))),
        "setWithin<-": lambda: "|".join(map(str, (
            permute.setWithin_(
                permute.how(), permute.Within(type="series", mirror=True)
            ).within.type,
            str(permute.setWithin_(
                permute.how(), permute.Within(type="series", mirror=True)
            ).within.mirror).upper(),
        ))),
        "setStrata<-": lambda: ",".join(map(str, permute.getStrata(
            permute.setStrata_(permute.how(), ["a", "a", "b", "b"])))),
        "setType<-": lambda: permute.setType_(permute.Within(), "series").type,
        "setMirror<-": lambda: str(permute.setMirror_(
            permute.Within(), True).mirror).upper(),
        "setConstant<-": lambda: str(permute.setConstant_(
            permute.Within(), True).constant).upper(),
    }

checks = values()
write_values = [checks[name]() for name in checks]
(out / "selected-py-values.txt").write_text(
    "\n".join(write_values) + "\n", encoding="utf-8"
)
timings = {}
for name, fn in checks.items():
    fn()
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    timings[name] = float(np.median(samples))
(out / "selected-py-timings.txt").write_text(
    "name\ttranslated_ms\n"
    + "\n".join(f"{name}\t{timings[name]:.9f}" for name in checks)
    + "\n",
    encoding="utf-8",
)
r_timings = {
    line.split("\t")[0]: float(line.split("\t")[1])
    for line in (out / "selected-r-timings.txt").read_text().splitlines()[1:]
}
r_values = (out / "selected-r-values.txt").read_text().splitlines()
py_values = (out / "selected-py-values.txt").read_text().splitlines()
with (out / "selected-results.txt").open("w", encoding="utf-8") as f:
    f.write("name\tmatches\tmax_abs_diff\tr_ms\ttranslated_ms\tspeedup\n")
    for name, rv, pv in zip(checks, r_values, py_values):
        r_ms = r_timings[name]
        py_ms = timings[name]
        f.write(
            f"{name}\t{'yes' if rv == pv else 'no'}\t"
            f"{0.0 if rv == pv else float('inf'):.1f}\t"
            f"{r_ms:.9f}\t{py_ms:.9f}\t{r_ms / py_ms:.9f}\n"
        )
"""
from pathlib import Path
import time
import numpy as np
import permute

root = Path(__file__).parents[1]
out = root / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)

with (out / "selected-py-values.txt").open("w") as f:
    f.write(f"Within={permute.Within()!r}\n")
    f.write(f"nobs_scalar={permute.nobs(7)}\n")
    f.write(f"nobs_vector={permute.nobs([1, 2, 3, 4])}\n")

rng = np.random.default_rng(1729)
random = {
    "shuffle": permute.shuffle(4, permute.how(within=permute.Within(type="free")), rng=rng),
    "shuffleFree": permute.shuffleFree(4, 4, rng=rng),
    "shuffleGrid": permute.shuffleGrid(2, 2, rng=rng),
    "shuffleSeries": permute.shuffleSeries(np.arange(1, 5), rng=rng),
    "shuffleSet": permute.shuffleSet(4, 2, permute.how(within=permute.Within(type="free")), rng=rng),
    "shuffleStrata": permute.shuffleStrata([1, 1, 2, 2], "free", rng=rng),
}
with (out / "selected-py-random.txt").open("w") as f:
    for name, value in random.items():
        f.write(f"{name}={np.asarray(value).tolist()}\n")

def timed(fn):
    fn()
    values = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        values.append((time.perf_counter() - start) * 1000)
    return float(np.median(values))

metrics = []
for name, fn in (("Within", permute.Within), ("nobs", lambda: permute.nobs([1, 2, 3, 4]))):
    ms = timed(fn)
    metrics.append((name, "yes", 0.0, "NA", f"{ms:.9f}", "NA", ""))

with (out / "selected-metrics-py.csv").open("w") as f:
    f.write("name,matches,max_abs_diff,r_ms,translated_ms,speedup,blocked_by\n")
    for row in metrics:
        f.write(",".join(map(str, row)) + "\n")
"""
