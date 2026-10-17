import statistics, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust.dr_predict import crimcoords
P=Path(__file__).parent
X=np.array([[1,2,3],[2,1,4],[4,3,2],[5,4,1],[6,2,3],[7,5,2]],float)
def one():
    z=crimcoords(X,["a","a","b","b","c","c"])
    return np.r_[z["means"].ravel(order="F"),z["B"].ravel(order="F"),z["W"].ravel(order="F"),z["evalues"],z["basis"].ravel(order="F"),z["projection"].ravel(order="F")]
if __name__=="__main__":
    v=one(); ts=[]
    for _ in range(20): s=time.perf_counter(); one(); ts.append((time.perf_counter()-s)*1000)
    e=np.loadtxt(P/"crimcoords-r-values.txt"); d=float(np.max(np.abs(v-e))); r=float((P/"crimcoords-r-ms.txt").read_text()); m=statistics.median(ts)
    print(f"matches {'true' if d<=1e-8 else 'false'}\nmax_abs_diff {d:.17g}\nr_ms {r:.17g}\ntranslated_ms {m:.17g}\nspeedup {r/m:.17g}")
