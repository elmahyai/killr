import statistics
import time

def one():
    from tools.textutil import parse_uri_reference
    uri = parse_uri_reference(["https://example.com/a?q=1#f", "file", ""])
    flat = []
    for key in ("scheme", "authority", "path", "query", "fragment"):
        flat.extend(row[key] for row in uri)
    return "|".join(flat) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
