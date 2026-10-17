import statistics
import time

def one():
    from tools.delim import delim_match
    x = ["a{bc}d", "a{b{c}d}", "no", "{a%}", "a\\%{b}", "x[y[z]w]"]
    return " ".join(str(item) for item in delim_match(x)) + " " + str(delim_match("x[y[z]w]", ["[", "]"])) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
