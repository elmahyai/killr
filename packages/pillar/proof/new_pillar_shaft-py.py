import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

from pillar.shaft import new_pillar_shaft


def one():
    shaft = new_pillar_shaft(["a", "b"], width=5, min_width=3, class_="pillar_shaft_demo")
    return "\n".join([shaft.classes[0], str(shaft.width), str(shaft.min_width), "|".join(shaft.data)])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
