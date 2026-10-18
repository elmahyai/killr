import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from fitdistrplus.batch_8db1ae45 import (llplot, llsurface, llcurve, mgedist,
    mledist, mmedist, msedist, plotdist, plotdistcens, ppcomp, ppcompcens,
    prefit, qmedist, qqcomp)

DATA = np.array([-0.2, 0.1, 0.3, 0.8, 1.2, 1.5])
PAR = {"mean": 0.0, "sd": 1.0}

def moment(x, order, weights=None):
    return float(np.mean(np.asarray(x) ** order))

def run(name):
    if name == "mledist": return mledist(DATA, "norm", start=[0, 1])
    if name == "qmedist": return qmedist(DATA, "norm", [.25, .75], start=[0, 1])
    if name == "mmedist": return mmedist(DATA, "norm", [1, 2], moment, start=[0, 1])
    if name == "mgedist": return mgedist(DATA, "norm", start=[0, 1])
    if name == "msedist": return msedist(DATA, "norm", start=[0, 1])
    if name == "plotdist": return plotdist(DATA, "norm", PAR)
    if name == "ppcomp": return ppcomp({"data": DATA, "distname": "norm", "estimate": [0, 1]})
    if name == "qqcomp": return qqcomp({"data": DATA, "distname": "norm", "estimate": [0, 1]})
    if name == "prefit": return prefit(DATA, "norm", feasible_par=[0, 1])
    if name == "llcurve": return llcurve(DATA, "norm", ["mean"], [-1], [1], fix_arg={"sd": 1})
    if name == "llsurface": return llsurface(DATA, "norm", ["mean", "sd"], [-1, .5], [1, 2])
    if name == "llplot": return llplot({"data": DATA, "distname": "norm", "estimate": [0, 1], "sd": [1, 1]})
    if name in ("plotdistcens", "ppcompcens"):
        cens = {"left": DATA, "right": DATA}
        return plotdistcens(cens, "norm", PAR) if name == "plotdistcens" else ppcompcens([{"data": DATA, "distname": "norm", "estimate": [0, 1]}])
    raise ValueError(name)
