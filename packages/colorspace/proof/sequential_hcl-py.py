import json
import statistics
import time

from colorspace.sequential_hcl import sequential_hcl


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "default": sequential_hcl(7, h=260, c=80, l=(35, 95), power=1),
        "defaults": sequential_hcl(7),
        "power_vec": sequential_hcl(7, h=245, c=(40, 75, 0), l=(30, 95), power=(0.8, 1.4)),
        "triangular": sequential_hcl(7, h=245, c=(40, 75, 0), l=(30, 95), power=1),
        "multi_hue": sequential_hcl(7, h=(260, 220), c=(50, 75, 0), l=(30, 95), power=1),
        "linear_chroma": sequential_hcl(7, h=(260, 60), c=60, l=(40, 95), power=1),
        "palette": sequential_hcl(7, palette="Blues 3"),
        "palette_override": sequential_hcl(7, palette="Viridis", l2=85),
        "rev": sequential_hcl(7, h=260, c=80, l=(35, 95), power=1, rev=True),
        "alpha": sequential_hcl(
            5, h=260, c=80, l=(35, 95), power=1, alpha=(1, 0.5, 0.25, 0.5, 1)
        ),
        "no_fixup": sequential_hcl(7, h=260, c=120, l=(35, 95), power=1, fixup=False),
        "grays": sequential_hcl(11, palette="Grays"),
        "bulk": sequential_hcl(256, h=260, c=80, l=(30, 90), power=1.5),
    }


sequential_hcl(7, h=260, c=80, l=(35, 95), power=1)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_vec(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
