import statistics
import time
from openssl import sha256, aes_cbc_encrypt

def one():
    key = bytes.fromhex(sha256("This is super secret"))
    return ",".join(str(b) for b in aes_cbc_encrypt(b"hello curl", key, bytes(range(1, 17))))

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
