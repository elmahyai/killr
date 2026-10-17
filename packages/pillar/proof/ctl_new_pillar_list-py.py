import json
import statistics
import time

from cli._options import options as cli_options

cli_options(**{"cli.unicode": True})

from pillar._vec import NULL, DataFrame, Factor, List

from pillar.column import ctl_new_pillar_list


def one():
    frame = DataFrame({"a": [1, 2, 3], "b": ["x", "yy", "zzz"], "c": [True, False, None]})
    head = DataFrame({name: values[:2] for name, values in frame.columns.items()})
    pillars = ctl_new_pillar_list(frame, head, width=30)
    return "\n---\n".join("\n".join(item.format()) for item in pillars)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
