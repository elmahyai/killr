import statistics
import time

from r_yaml import yaml_load

def one():
    value = yaml_load("flag: y\nclock: 1:20\n")
    flag = "TRUE" if value["flag"] else "FALSE"
    return f"{flag},{value['clock']}"

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
