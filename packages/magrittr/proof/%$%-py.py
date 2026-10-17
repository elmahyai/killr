import json
import statistics
import time

from magrittr.pipe import exposition


def one():
    return exposition({"z": [1, 2, 3]}, lambda z: sum(z))


sentence = "data.frame(z = 1:3) %$% sum(z) returns 6.\n"
path = "/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/%$%-python.txt"
with open(path, "w", encoding="utf-8") as handle:
    handle.write(sentence)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": [value], "median_ms": statistics.median(elapsed)}))
