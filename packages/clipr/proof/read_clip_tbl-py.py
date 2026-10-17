import json
import statistics
import time

from clipr import read_clip_tbl

rows = ["Name's\tAge", "Alice\t30", "Bob\t25"]


def one():
    return read_clip_tbl(rows)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({
    "columns": value.columns,
    "row_names": value.row_names,
    "median_ms": statistics.median(elapsed),
}))
