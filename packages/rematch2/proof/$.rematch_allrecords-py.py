import statistics
import time

from rematch2 import dollar_rematch_allrecords, re_exec_all
pos = re_exec_all(["  Ben Franklin and Jefferson Davis", "\tMillard Fillmore"], "(?<first>[[:upper:]][[:lower:]]+) (?<last>[[:upper:]][[:lower:]]+)")
def one():
    return ",".join("+".join(row) for row in dollar_rematch_allrecords(pos["first"], "match"))

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
