import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from listenv import (ListEnv, as_listenv, dim_na, get_variable, listenv,
                     map, mapping, parse_env_subset, undim)

name = os.path.basename(__file__).removesuffix("-py.py")

def run():
    if name == "listenv":
        return listenv(1, 2, a=3).as_list()
    if name == "as.listenv":
        return as_listenv({"a": 1, "b": 2}).as_list()
    if name == "mapping":
        return mapping(listenv(a=1, b=2))
    if name == "map":
        return map(listenv(a=1))
    if name == "get_variable":
        x = listenv(a=1)
        return [get_variable(x, "a"), get_variable(x, 3), len(x)]
    if name == "dim_na<-":
        x = listenv(1, 2, 3, 4, 5, 6)
        dim_na(x, [2, None])
        return list(x.dim)
    if name == "undim":
        x = listenv(1, 2)
        x.dim = [2, 1]
        undim(x)
        return x.dim
    if name == "parse_env_subset":
        return parse_env_subset("x[[2]]")
    raise ValueError(name)

result = run()
times = []
for _ in range(20):
    t = time.perf_counter()
    run()
    times.append((time.perf_counter() - t) * 1000)
print(json.dumps({"result": result, "translated_ms": statistics.median(times)}))
