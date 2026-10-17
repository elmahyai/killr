import statistics
import time

def one():
    from tools.convert import to_html
    msgs = []
    for value in (1.0, "a", True, None):
        try:
            to_html(value)
            msgs.append("")
        except ValueError as exc:
            msgs.append(str(exc))
    return "\n".join(msgs) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
