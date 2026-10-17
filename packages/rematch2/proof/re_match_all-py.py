import statistics
import time

from rematch2 import re_match_all
notes = ["  Ben Franklin and Jefferson Davis", "\tMillard Fillmore"]
pattern = "(?<first>[[:upper:]][[:lower:]]+) (?<last>[[:upper:]][[:lower:]]+)"
def one():
    return ",".join("+".join(row) for row in re_match_all(notes, pattern)["first"])

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
