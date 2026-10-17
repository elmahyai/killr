import json
import statistics
import time

from colorspace.diverge_hcl import diverge_hcl


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "default": diverge_hcl(7),
        "power_vec": diverge_hcl(7, h=(260, 0), c=80, l=(35, 95), power=(0.8, 1.4)),
        "cmax": diverge_hcl(7, h=(260, 0), c=(80, 100), l=(35, 95), power=1),
        "palette": diverge_hcl(7, palette="Tropic", h2=0),
        "odd_n": diverge_hcl(11, h=(260, 0), c=80, l=(30, 90), power=1.5),
        "even_n": diverge_hcl(10, h=(260, 0), c=80, l=(30, 90), power=1.5),
        "single": diverge_hcl(1),
        "rev": diverge_hcl(7, rev=True),
        "alpha": diverge_hcl(5, alpha=(1, 0.5, 0.25, 0.5, 1)),
        "no_fixup": diverge_hcl(7, h=(260, 0), c=120, l=(35, 95), power=1, fixup=False),
        "named": diverge_hcl(7, palette="Blue-Red 3"),
        "bulk": diverge_hcl(256),
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
