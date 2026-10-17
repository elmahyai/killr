from openssl import read_ed25519_key, ed25519_sign

def one():
    key = read_ed25519_key(bytes(range(1, 33)))
    return ",".join(str(b) for b in ed25519_sign(b"hello", key))

import statistics
import time
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
