import json
import statistics
import time

from colorspace.deutanomaly_cvd import deutanomaly_cvd


def one():
    tables = deutanomaly_cvd()
    names = sorted(tables.keys(), key=int)
    return {
        "names": names,
        "matrices": [tables[name].tolist() for name in names],
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {**value, "median_ms": statistics.median(elapsed)}
print(json.dumps(payload))
