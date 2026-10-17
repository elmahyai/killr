import statistics
import time
from curl import parse_headers

def one():
    return "|".join(parse_headers("HTTP/1.1 200 OK\r\nA: b\r\n\r\nHTTP/1.1 201\r\nC: d\r\n"))

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
