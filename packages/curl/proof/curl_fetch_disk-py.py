import statistics
import time
from curl import curl_fetch_disk

def one():
    import tempfile
    src = tempfile.NamedTemporaryFile(delete=False)
    src.write(b"hello-file")
    src.close()
    dest = tempfile.NamedTemporaryFile(delete=False)
    dest.close()
    res = curl_fetch_disk("file://" + src.name, dest.name)
    return open(res["content"], "rb").read().decode()

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
