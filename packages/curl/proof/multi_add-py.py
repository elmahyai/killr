import statistics
import time
from curl import new_handle, new_pool, multi_add, multi_run

def one():
    import tempfile
    handle = tempfile.NamedTemporaryFile(delete=False)
    handle.write(b"Zed")
    handle.close()
    got = []
    h = new_handle(url="file://" + handle.name)
    pool = new_pool()
    multi_add(h, done=lambda data: got.append(data["content"].decode()), pool=pool)
    multi_run(pool)
    return got[0]

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
