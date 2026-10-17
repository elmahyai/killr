from pathlib import Path
import statistics, subprocess, tempfile, time, sys
import numpy as np
sys.path.insert(0, str(Path(__file__).parents[1]))
import permute
root=Path(__file__).parents[1]; out=root/'docs'/'output'; out.mkdir(parents=True, exist_ok=True)
rfile=out/'setNperm-r.txt'; pyfile=out/'setNperm-python.txt'; result=out/'setNperm-result.txt'
rscript = 'library(permute, lib.loc="/tmp/permute-lib")\nf <- function() { x <- how(); setNperm(x) <- 17L; paste0(\'nperm=\', x$nperm) }\nwriteLines(f(), "{rfile}")\nf(); z <- numeric(20)\nfor (i in seq_len(20)) { t <- Sys.time(); f(); z[i] <- as.numeric(difftime(Sys.time(), t, units="secs"))*1000 }\nwrite(paste0("r_ms=", median(z)), "{result}", append=TRUE)\n'.replace("{rfile}", str(rfile)).replace("{result}", str(result))
with tempfile.NamedTemporaryFile('w', suffix='.R', delete=False) as fh:
    fh.write(rscript); rpath=fh.name
subprocess.run(['Rscript','--vanilla',rpath], check=True)
def fn():
    x=permute.how(); permute.setNperm_(x,17); return f'nperm={x.nperm}'
fn(); ts=[]
for _ in range(20):
    t=time.perf_counter(); fn(); ts.append((time.perf_counter()-t)*1000)
value=fn(); pyvals=[str(v) for v in (value if isinstance(value,list) else [value])]
pyfile.write_text("\n".join(pyvals)+"\n")
rvals=rfile.read_text().splitlines(); pvals=pyfile.read_text().splitlines()
if len(rvals)!=len(pvals): raise AssertionError((rvals,pvals))
max_abs=0.0
for a,b in zip(rvals,pvals):
    ak,av=a.split("=",1); bk,bv=b.split("=",1)
    if ak!=bk: raise AssertionError((a,b))
    try: max_abs=max(max_abs,abs(float(av)-float(bv)))
    except ValueError:
        if av!=bv: raise AssertionError((a,b))
r_ms=float([x for x in result.read_text().splitlines() if x.startswith("r_ms=")][-1].split("=",1)[1])
py_ms=statistics.median(ts); speed=r_ms/py_ms if py_ms else float("inf")
result.write_text("name='setNperm'\nmatches="+('yes' if max_abs <= 1e-8 else 'no')+f"\nmax_abs_diff={max_abs}\nr_ms={r_ms}\ntranslated_ms={py_ms}\nspeedup={speed}\n")
print(result.read_text(), end="")
