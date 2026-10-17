import json
import statistics
import time

from crayon import *
options(**{"crayon.enabled": True, "width": 80})

def one():
    text = concat(concat(red("I am red---"), green("and I am green-")), underline("I underlined"))
    return col_strsplit(text, "[-]+")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
