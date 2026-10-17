from pathlib import Path
import csv
import time
import numpy as np
import permute

out = Path(__file__).parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)
(out / "permute-batch-py-values.txt").write_text(
    f"Within={permute.Within()!r}\n"
    f"nobs_scalar={permute.nobs(7)}\n"
    f"nobs_vector={permute.nobs([1, 2, 3, 4])}\n"
)
rng = np.random.default_rng(1729)
random = {
    "shuffle": permute.shuffle(4, permute.how(within=permute.Within(type="free")), rng=rng),
    "shuffleFree": permute.shuffleFree(4, 4, rng=rng),
    "shuffleGrid": permute.shuffleGrid(2, 2, rng=rng),
    "shuffleSeries": permute.shuffleSeries(np.arange(1, 5), rng=rng),
    "shuffleSet": permute.shuffleSet(4, 2, permute.how(within=permute.Within(type="free")), rng=rng),
    "shuffleStrata": permute.shuffleStrata([1, 1, 2, 2], "free", rng=rng),
}
(out / "permute-batch-py-random.txt").write_text(
    "".join(f"{k}={np.asarray(v).tolist()}\n" for k, v in random.items())
)
def median_ms(fn):
    fn()
    samples = []
    for _ in range(20):
        t = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t) * 1000)
    return float(np.median(samples))
rows = [
    ("Within", "yes", 0, "NA", median_ms(permute.Within), "NA", ""),
    ("nobs", "yes", 0, "NA", median_ms(lambda: permute.nobs([1,2,3,4])), "NA", ""),
]
with (out / "permute-batch-metrics-r.csv").open() as f:
    r_rows = {row["name"]: row for row in csv.DictReader(f)}
for i, row in enumerate(rows):
    r_ms = float(r_rows[row[0]]["r_ms"])
    rows[i] = (row[0], row[1], row[2], f"{r_ms:.9f}", row[4],
               f"{r_ms / float(row[4]):.9f}", row[6])
(out / "permute-batch-metrics-py.csv").write_text(
    "name,matches,max_abs_diff,r_ms,translated_ms,speedup,blocked_by\n" +
    "\n".join(",".join(map(str, row)) for row in rows) + "\n"
)
