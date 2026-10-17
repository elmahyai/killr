import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.num_colors": 8, "cli.unicode": True})

from pillar.parts import new_pillar_component


def one():
    x = new_pillar_component([["a", "b", "c"]], width=1)
    y = new_pillar_component([["a", "b", "c"]], width=5, min_width=2)
    return {
        "width": x.width,
        "min_width": x.min_width,
        "values": x.x[0],
        "width2": y.width,
        "min2": y.min_width,
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
