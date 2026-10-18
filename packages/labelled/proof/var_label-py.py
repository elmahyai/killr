import importlib.util, statistics, time, sys, numpy as np
spec = importlib.util.spec_from_file_location("labels", "packages/labelled/labelled/labels.py")
m = importlib.util.module_from_spec(spec); sys.modules["labels"] = m; spec.loader.exec_module(m)
x = m.HavenLabelled(np.array([1, 2, 3]), variable_label="demo")
one = m.var_label(x); t = []
for _ in range(20):
    a = time.perf_counter(); m.var_label(x); t.append((time.perf_counter()-a)*1000)
print(f"value={one}\npy_ms={statistics.median(t):.17g}")
