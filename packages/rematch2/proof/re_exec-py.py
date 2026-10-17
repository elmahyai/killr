import statistics
import time

from rematch2 import re_exec
notes = ["  Ben Franklin and Jefferson Davis", "\tMillard Fillmore"]
pattern = "(?<first>[[:upper:]][[:lower:]]+) (?<last>[[:upper:]][[:lower:]]+)"
def one():
    pos = re_exec(notes, pattern)
    return ",".join(f"{m}:{s}:{e}" for m, s, e in zip(pos["first"].match, pos["first"].start, pos["first"].end))

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
