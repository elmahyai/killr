from openssl import x25519_keygen, x25519_diffie_hellman

def one():
    a = x25519_keygen()
    b = x25519_keygen()
    sec = x25519_diffie_hellman(a, b.pubkey)
    other = x25519_diffie_hellman(b, a.pubkey)
    return "32" if sec == other and len(sec) == 32 else "bad"

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
