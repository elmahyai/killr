import json, statistics, time
import importlib.util, pathlib, sys
_spec=importlib.util.spec_from_file_location("labelled_val_labels", pathlib.Path(__file__).parents[1]/"labelled"/"val_labels.py")
_mod=importlib.util.module_from_spec(_spec); sys.modules["labelled_val_labels"]=_mod; _spec.loader.exec_module(_mod)
from labelled_val_labels import *
def one():
    x=labelled([1,2], {"one":1,"two":2})
    return val_label(x, 2)
value=one(); elapsed=[]
for _ in range(20):
    t=time.perf_counter(); one(); elapsed.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(elapsed)}))
