from openssl import ed25519_keygen, ed25519_sign, ed25519_verify

def one():
    key = ed25519_keygen()
    return ed25519_verify(b"hello", ed25519_sign(b"hello", key), key.pubkey)

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
