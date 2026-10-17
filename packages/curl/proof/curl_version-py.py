import statistics
import time
from curl import curl_version

def one():
    v = curl_version()
    flag = "TRUE" if v["ipv6"] else "FALSE"
    return "|".join([v["version"], v["ssl_version"], flag, v["protocols"][0], v["protocols"][-1]])

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
