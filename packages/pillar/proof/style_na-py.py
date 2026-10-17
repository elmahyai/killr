import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.num_colors": 8})

from pillar.styles import style_na


def one():
    return style_na(["NA", "", None])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
