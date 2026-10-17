import statistics
import time

def one():
    import hashlib
    from tools.data import charset_to_unicode
    ch = charset_to_unicode()
    rows = "\n".join(",".join(str(v) for v in row) for row in ch["values"])
    digest = hashlib.md5(rows.encode()).hexdigest()
    return f"CHAR {len(ch['values'])} {len(ch['columns'])} {','.join(ch['columns'])} {digest}\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
