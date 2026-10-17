import statistics
import time

from digest.aes import AES

key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
plaintext = bytes.fromhex("00112233445566778899aabbccddeeff")


def one():
    return AES(key).encrypt(plaintext)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print('{"hex":"%s","median_ms":%.17g}' % (value.hex(), statistics.median(elapsed)))
