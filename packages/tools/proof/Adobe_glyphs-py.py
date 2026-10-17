import statistics
import time

def one():
    import hashlib
    from tools.data import adobe_glyphs
    g = adobe_glyphs()
    blob = "|".join(f"{a}={u}" for a, u in zip(g["adobe"], g["unicode"]))
    digest = hashlib.md5(blob.encode()).hexdigest()
    return f"GLYPH {len(g['adobe'])} {digest} {g['adobe'][0]} {g['unicode'][0]} {g['adobe'][-1]} {g['unicode'][-1]}\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
