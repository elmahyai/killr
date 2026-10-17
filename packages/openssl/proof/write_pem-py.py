import statistics
import time

from openssl import read_ed25519_key
from openssl.write_pem import write_pem


def one():
    key = read_ed25519_key(bytes(range(1, 33)))
    return write_pem(key)


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
