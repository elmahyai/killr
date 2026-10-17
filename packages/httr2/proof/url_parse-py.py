import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr2")
from httr2.url_parse import url_parse


def fmt(value):
    return "NULL" if value is None else str(value)


def one():
    u = url_parse("http://user:pass@example.com:81/path?a=1&b=2&c={1{2}3}#frag")
    if u.query is None:
        query = "NULL"
    else:
        query = "&".join(f"{name}={value}" for name, value in u.query)
    return "|".join(
        [
            "httr2_url",
            fmt(u.scheme),
            fmt(u.hostname),
            fmt(u.username),
            fmt(u.password),
            fmt(u.port),
            fmt(u.path),
            query,
            fmt(u.fragment),
        ]
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
