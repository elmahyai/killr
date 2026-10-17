from r_sys import eval_safe
try:
    eval_safe(1)
except RuntimeError as exc:
    print(exc)
