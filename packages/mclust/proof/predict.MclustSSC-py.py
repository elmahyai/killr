import csv, statistics, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust.mclust_ssc import mclust_ssc
from mclust.dr_predict import predict_MclustSSC
P=Path(__file__).parent
X=np.loadtxt(P/"MclustSSC_X.csv",delimiter=",",skiprows=1)
with (P/"MclustSSC_class.csv").open() as h: cl=[float("nan") if r["class"] in ("","NA") else r["class"] for r in csv.DictReader(h)]
def one():
    m=mclust_ssc(X,cl,verbose=False); p=predict_MclustSSC(m,X[:6]); return np.r_[p["z"].ravel(order="F"),np.argmax(p["z"],axis=1)+1]
if __name__=="__main__":
    v=one(); ts=[]
    for _ in range(20): s=time.perf_counter(); one(); ts.append((time.perf_counter()-s)*1000)
    e=np.loadtxt(P/"predict.MclustSSC-r-values.txt"); d=float(np.max(np.abs(v-e))); r=float((P/"predict.MclustSSC-r-ms.txt").read_text()); m=statistics.median(ts)
    print(f"matches {'true' if d<=1e-8 else 'false'}\nmax_abs_diff {d:.17g}\nr_ms {r:.17g}\ntranslated_ms {m:.17g}\nspeedup {r/m:.17g}")
