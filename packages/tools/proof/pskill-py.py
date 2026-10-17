import statistics
import time

def one():
    import subprocess, time
    from tools.process import pskill
    proc = subprocess.Popen(["sleep", "30"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = pskill(proc.pid)
    proc.wait(timeout=2)
    gone = pskill(proc.pid)
    return f"{str(ok).upper()} {str(gone).upper()} {str(pskill(-1)).upper()} {str(pskill(10**9)).upper()}\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
