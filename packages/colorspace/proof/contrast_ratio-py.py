import json
import statistics
import time

from colorspace.contrast_ratio import _DEFAULT_PALETTE, contrast_ratio


def _json_ratio(value):
    if getattr(value, "ndim", 0) == 2 and value.shape[1] == 2:
        return value.tolist()
    return [float(x) for x in value]


def one():
    return {
        "palette_wcag": contrast_ratio(_DEFAULT_PALETTE, "white"),
        "hex_pair": contrast_ratio(["#FF0000", "#00FF00"], ["white", "black"]),
        "named_apca": contrast_ratio(["red", "blue"], "white", algorithm="APCA"),
        "recycle": contrast_ratio("red", ["white", "black", "gray"]),
        "palette_int": contrast_ratio(list(range(1, 9)), "white"),
        "transparent": contrast_ratio("transparent", "#000000"),
        "short_hex": contrast_ratio(["#abc", "#123456"], "white"),
        "near_white_apca": contrast_ratio("#fefefe", "#ffffff", algorithm="APCA"),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {key: _json_ratio(val) for key, val in value.items()}
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
