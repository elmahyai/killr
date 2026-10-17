import json
import statistics
import time

from colorspace.qualitative_hcl import qualitative_hcl


def _json_vec(values):
    return [None if value is None else str(value) for value in values]


def one():
    return {
        "default5": qualitative_hcl(5),
        "custom_h": qualitative_hcl(7, h=30, c=50, l=65),
        "palette": qualitative_hcl(6, palette="Set 3"),
        "single": qualitative_hcl(1),
        "empty": qualitative_hcl(0),
        "alpha_vec": qualitative_hcl(5, alpha=(1, 0.5, 0.25, 0.5, 1)),
        "alpha_scalar": qualitative_hcl(4, alpha=0.75),
        "no_fixup": qualitative_hcl(8, c=100, l=50, fixup=False),
        "rev": qualitative_hcl(5, rev=True),
        "bulk": qualitative_hcl(256),
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
