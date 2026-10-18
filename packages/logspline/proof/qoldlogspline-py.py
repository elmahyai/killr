from _batch_common import OLD, run, qoldlogspline
run("qoldlogspline", lambda x: qoldlogspline(x, OLD), [0.1, 0.5, 0.9])
