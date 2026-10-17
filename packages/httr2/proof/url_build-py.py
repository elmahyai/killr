import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/curl")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr2")
from httr2.url_build import url_build
from httr2.url_parse import url_parse


def one():
    return url_build(
        url_parse(
            "http://user:pass@example.com:81/a:b/foo%20bar/?a=1&b=2&c={1{2}3}#frag"
        )
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
