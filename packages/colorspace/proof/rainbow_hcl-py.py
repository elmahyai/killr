import json
import statistics
import time

from colorspace.rainbow_hcl import rainbow_hcl


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "default12": rainbow_hcl(12),
        "custom_hue": rainbow_hcl(7, c=60, l=65, start=30, end=300),
        "single": rainbow_hcl(1),
        "empty": rainbow_hcl(0),
        "alpha_vec": rainbow_hcl(5, alpha=(1, 0.5, 0.25, 0.5, 1)),
        "alpha_scalar": rainbow_hcl(4, alpha=0.75),
        "no_fixup": rainbow_hcl(8, c=100, l=50, fixup=False),
        "bulk": rainbow_hcl(256),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_vec(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
