import statistics
import time
from curl import curl_modify_url, curl_parse_url

def one():
    url = "https://jerry:secret@google.com:888/foo/bar?test=123#bla"
    out = curl_parse_url(url)
    return curl_modify_url(out)

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
