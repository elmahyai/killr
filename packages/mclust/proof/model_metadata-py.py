import statistics, time, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mclust.model_metadata import *

def run(name, fn):
    value = fn()
    times = []
    for _ in range(20):
        t = time.perf_counter(); fn(); times.append((time.perf_counter()-t)*1000)
    print(name, repr(value), statistics.median(times))

run("checkModelName", lambda: checkModelName("EEE"))
run("decomp2sigma", lambda: decomp2sigma(2, 1, 2., np.array([1., 3.]))["sigma"].ravel().tolist())
run("defaultPrior", lambda: defaultPrior(np.array([[1.,2.],[2.,4.],[3.,6.]]), 2, "EEE")["dof"])
run("dupPartition", lambda: dupPartition(np.array([1.,1.,2.,2.])).tolist())
run("mclustModel", lambda: mclustModel(np.arange(4), {"EEE": 1., "VVI": 2.})["modelName"])
run("mclustModelNames", lambda: mclustModelNames("EEE")["type"])
run("mclustVariance", lambda: mclustVariance("VVI", 2, 3)["shape"].shape)
run("nMclustParams", lambda: nMclustParams("VVV", 2, 3))
run("nVarParams", lambda: nVarParams("EEE", 2, 3))
run("partconv", lambda: partconv([4,2,4,7]).tolist())
run("partuniq", lambda: partuniq([[1,2],[1,2],[2,3]]).tolist())
run("priorControl", lambda: priorControl(shrinkage=.1))
run("sigma2decomp", lambda: sigma2decomp(np.diag([2.,8.]))["modelName"])
