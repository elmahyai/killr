import statistics
import time

def one():
    from tools.latex import deparse_latex
    nodes = [
        {"tag": "MACRO", "text": "\\emph"},
        {"tag": "BLOCK", "body": [{"tag": "TEXT", "text": "x"}]},
        {"tag": "MATH", "body": [{"tag": "TEXT", "text": "y"}]},
    ]
    return deparse_latex(nodes) + "\n" + deparse_latex(nodes, drop_braces=True) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
