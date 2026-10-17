import json
import statistics
import time
from fansi.unhandled_ctl import unhandled_ctl

def one():
    return unhandled_ctl(["\033[41mhello world\033[m", "foo\033[22>m", "\033[999mbar", "baz \033[31#3m", "a\033[31k", "hello\033m world"], term_cap=["bright", "256"])

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

rows = value
shown = [f"{a}:{b}:{c}:{d}:{e}" for a, b, c, d, e in zip(rows["index"], rows["start"], rows["stop"], rows["error"], rows["translated"])]
print(json.dumps({"value": shown, "median_ms": statistics.median(elapsed)}))
