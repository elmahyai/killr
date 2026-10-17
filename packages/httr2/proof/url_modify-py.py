import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/curl")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr2")
from httr2.url_modify import url_modify


def one():
    return url_modify(
        "http://user:pass@hadley.nz:81/abc?a=1#frag",
        scheme="https",
        path="a:b/foo bar/",
        query={"c": 3},
        fragment="section-1",
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
elif value is None:
    shown = "NULL"
else:
    shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
