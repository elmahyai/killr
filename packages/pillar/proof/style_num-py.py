import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.num_colors": 8})

from pillar._options import options as pillar_options
from pillar.styles import style_num

pillar_options(**{"pillar.subtle_num": False, "pillar.neg": True, "pillar.subtle": True})


def one():
    return (
        style_num(["123", "456"], [True, False])
        + style_num(["123", "456"], [True, False], [False, False])
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
