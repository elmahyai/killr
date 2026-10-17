import os, sys, time, statistics
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from DEoptimR import JDEoptim, NCDEoptim, SPJDEoptim

pop = np.array([[1., -1., 0., 1.], [2., .5, 1., -2.]])
cases = [
    ("JDEoptim", lambda: JDEoptim([-2,-2], [2,2], lambda x: np.sum(x*x),
     NP=0, maxiter=0, add_to_init_pop=pop, details=True)),
    ("SPJDEoptim", lambda: SPJDEoptim([-2,-2], [2,2], lambda x: np.sum(x*x),
     NP=0, maxiter=0, add_to_init_pop=pop, sequential_eval="both", details=True)),
    ("NCDEoptim", lambda: NCDEoptim([-2,-2], [2,2], lambda x: np.sum(x*x),
     NP=0, maxiter=0, add_to_init_pop=pop)),
]
os.makedirs(os.path.join(os.path.dirname(__file__), "../docs/output"), exist_ok=True)
with open(os.path.join(os.path.dirname(__file__), "../docs/output/python_values.txt"), "w") as out:
    for name, call in cases:
        call()
        ts=[]
        for _ in range(20):
            t=time.perf_counter(); z=call(); ts.append(time.perf_counter()-t)
        vals=[]
        for k,v in z.items():
            if isinstance(v, (int,float,np.number)): vals.append(float(v))
            elif isinstance(v,np.ndarray): vals.extend(v.ravel(order="F").tolist())
        out.write(f"{name} {' '.join(f'{x:.17g}' for x in vals)}\n")
        print(name, "R ms: see r_proof.R", f"Python ms: {statistics.median(ts)*1000:.6g}")
