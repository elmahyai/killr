import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.num_colors": 8, "cli.unicode": True})

from pillar._options import options as pillar_options
from pillar.parts import new_pillar_title

pillar_options(
    **{"pillar.bold": False, "pillar.subtle": True, "pillar.min_title_chars": 20}
)


def one():
    return {
        "trees": new_pillar_title(["Girth", "Height", "Volume"]).format(),
        "letters": new_pillar_title("letters").format(),
        "trunc": new_pillar_title(["hello", "hi"]).format(width=4),
        "empty": new_pillar_title(None).format(),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
