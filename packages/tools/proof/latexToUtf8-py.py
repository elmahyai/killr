import statistics
import time

def one():
    from tools.latex import deparse_latex, latex_to_utf8
    def show(nodes):
        return deparse_latex(latex_to_utf8(nodes))
    return "\n".join([
        show([{"tag": "MACRO", "text": "\\'"}, {"tag": "TEXT", "text": "e"}]),
        show([{"tag": "MACRO", "text": "\\'"}, {"tag": "TEXT", "text": " e"}]),
        show([{"tag": "MACRO", "text": "\\aa"}]),
        show([{"tag": "MACRO", "text": "\\'"}, {"tag": "BLOCK", "body": [{"tag": "TEXT", "text": "e"}]}]),
    ]) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
