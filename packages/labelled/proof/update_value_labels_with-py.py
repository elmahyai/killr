import json, statistics, time
import importlib.util, pathlib, sys
_spec=importlib.util.spec_from_file_location("labelled_val_labels", pathlib.Path(__file__).parents[1]/"labelled"/"val_labels.py")
_mod=importlib.util.module_from_spec(_spec); sys.modules["labelled_val_labels"]=_mod; _spec.loader.exec_module(_mod)
from labelled_val_labels import *
def one():
    d={"a":labelled([1,2], {"yes":1,"no":2})}
    return list(val_labels(update_value_labels_with(d, str.upper)["a"]).keys())
value=one(); elapsed=[]
for _ in range(20):
    t=time.perf_counter(); one(); elapsed.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"median_ms":statistics.median(elapsed)}))
