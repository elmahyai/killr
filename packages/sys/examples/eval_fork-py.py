from r_sys import eval_fork
try:
    eval_fork(1)
except RuntimeError as exc:
    print(exc)
