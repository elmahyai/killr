from _batch_common import FIT, run, rlogspline
run("rlogspline", lambda x: rlogspline(x, FIT), 5)
