import statistics
import time

from openssl import read_x25519_key
from openssl.ec_dh import ec_dh


def one():
    k1 = read_x25519_key(bytes(range(1, 33)))
    k2 = read_x25519_key(bytes(range(32, 0, -1)))
    return ",".join(str(b) for b in ec_dh(k1, k2.pubkey))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
else:
    shown = str(value)
print("VALUE " + shown.replace("\n", " / "))
print(f"MS {statistics.median(elapsed):.17g}")
