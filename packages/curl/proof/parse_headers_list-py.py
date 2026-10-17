import statistics
import time
from curl import parse_headers_list

def one():
    h = parse_headers_list("HTTP/1.1 200\r\nContent-Type: text/plain\r\n")
    return "|".join(f"{name}={value}" for name, value in h.items())

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
