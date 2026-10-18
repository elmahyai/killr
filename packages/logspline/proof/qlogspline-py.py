from _batch_common import FIT, run, qlogspline
run("qlogspline", lambda x: qlogspline(x, FIT), [0.1, 0.5, 0.9])
