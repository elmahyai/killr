import json
import statistics
import time

from colorspace.diverging_hcl import diverging_hcl


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "default": diverging_hcl(7, h=(260, 0), c=80, l=(35, 95), power=1),
        "power_vec": diverging_hcl(7, h=(260, 0), c=80, l=(35, 95), power=(0.8, 1.4)),
        "cmax": diverging_hcl(7, h=(260, 0), c=(80, 100), l=(35, 95), power=1),
        "palette": diverging_hcl(7, palette="Tropic", h2=0),
        "odd_n": diverging_hcl(11, h=(260, 0), c=80, l=(30, 90), power=1.5),
        "even_n": diverging_hcl(10, h=(260, 0), c=80, l=(30, 90), power=1.5),
        "single": diverging_hcl(1, h=(260, 0), c=80, l=(35, 95), power=1),
        "rev": diverging_hcl(7, h=(260, 0), c=80, l=(35, 95), power=1, rev=True),
        "alpha": diverging_hcl(
            5, h=(260, 0), c=80, l=(35, 95), power=1, alpha=(1, 0.5, 0.25, 0.5, 1)
        ),
        "no_fixup": diverging_hcl(
            7, h=(260, 0), c=120, l=(35, 95), power=1, fixup=False
        ),
        "named": diverging_hcl(7, palette="Blue-Red 3"),
        "bulk": diverging_hcl(256, h=(260, 0), c=80, l=(30, 90), power=1.5),
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
