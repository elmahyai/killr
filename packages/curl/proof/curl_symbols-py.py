import statistics
import time

from curl.curl_symbols import curl_symbols


def _fmt(value):
    if value is None:
        return "NA"
    return str(value)


def one():
    rows = curl_symbols("CURLAUTH")
    return "|".join(
        "=".join(
            [
                row["name"],
                _fmt(row["introduced"]),
                _fmt(row["deprecated"]),
                _fmt(row["removed"]),
                _fmt(row["value"]),
                _fmt(row["type"]),
            ]
        )
        for row in rows
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
