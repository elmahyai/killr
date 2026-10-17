import statistics
import time
from curl import curl_parse_url

def one():
    u = curl_parse_url("https://jerry:secret@google.com:888/foo/bar?test=123#bla")
    params = "|".join(f"{k}={v}" for k, v in u["params"].items())
    return "|".join([u["url"], u["scheme"], u["host"], u["port"], u["path"], u["user"], u["password"], u["fragment"], params])

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
