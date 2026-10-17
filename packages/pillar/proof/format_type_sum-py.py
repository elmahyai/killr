import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.num_colors": 8})

from pillar._options import options as pillar_options
from pillar.styles import format_type_sum

pillar_options(**{"pillar.subtle": True})


def one():
    return format_type_sum("dbl", None)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
