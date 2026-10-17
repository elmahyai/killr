import statistics
import time

from rematch2 import re_match
dates = ["2016-04-20", "1977-08-08", "not a date", "2016", "76-03-02", "2012-06-30", "2015-01-21 19:58"]
pattern = "(?<year>[0-9]{4})-(?<month>[0-1][0-9])-(?<day>[0-3][0-9])"
def one():
    return ",".join("NA" if v is None else v for v in re_match(dates, pattern)["year"])

ans = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(ans)
print(f"{statistics.median(elapsed):.17g}")
