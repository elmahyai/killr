import statistics
import time

def one():
    from tools.latex import encoded_text_to_latex
    return encoded_text_to_latex("A caf\u00e9", "UTF-8") + "\n" + encoded_text_to_latex("A", "latin1") + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
