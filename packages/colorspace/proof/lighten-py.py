import json
import statistics
import time

from colorspace.lighten import lighten


def _json_vec(values):
    out = []
    for value in values:
        if value is None:
            out.append(None)
        elif isinstance(value, list):
            out.extend(_json_vec(value))
        else:
            out.append(str(value))
    return out


CL = ["#61A9D9", "#ADD668", "#E6D152", "#CE6BAF", "#797CBA"]
HEXES = ["#FF0000", "#00FF0080", "#336699", "#AABBCCDD"]


def one():
    bulk = [f"#{i:02X}{(255 - i):02X}{(i + 17) % 256:02X}" for i in range(256)]
    return {
        "default": lighten(CL, 0.15),
        "hls": lighten(CL, 0.15, space="HLS"),
        "combined": lighten(CL, 0.3, space="combined"),
        "absolute": lighten(HEXES, 0.2, method="absolute"),
        "zero": lighten(["#112233", "#445566"], [0.2, 0]),
        "recycle": lighten("#112233", [0.1, 0.2, 0.3]),
        "negative": lighten(CL, -0.1),
        "named": lighten({"red": "#FF0000", "blue": "#0000FF"}),
        "palette": lighten([1, 2, 3], 0.25),
        "no_fixup": lighten(["#FF0000", "#010101"], 0.5, fixup=False),
        "bulk": lighten(bulk, 0.12),
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
