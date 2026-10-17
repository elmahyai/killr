import statistics
import time

from rematch2 import re_exec_all
notes = ["  Ben Franklin and Jefferson Davis", "\tMillard Fillmore"]
pattern = "(?<first>[[:upper:]][[:lower:]]+) (?<last>[[:upper:]][[:lower:]]+)"
def one():
    pos = re_exec_all(notes, pattern)
    return ",".join("+".join(f"{m}:{s}:{e}" for m, s, e in zip(row_m, row_s, row_e)) for row_m, row_s, row_e in zip(pos["first"].match, pos["first"].start, pos["first"].end))

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
