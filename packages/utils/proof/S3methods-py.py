import statistics
import time

from utils.s3_methods import S3methods
from utils.s3_session import BindingEnviron


def _generic(name: str):
    def method(x):
        raise NotImplementedError

    method.__name__ = name
    method.__r_usemethod__ = name
    return method


def one():
    g = "killrS3methodsProof"
    env = BindingEnviron(
        {
            g: _generic(g),
            f"{g}.alpha": lambda x: x,
            f"{g}.beta": lambda x: x,
        }
    )
    res = S3methods(g, envir=env, use_env=True, drop_path=True)
    info = res.info
    return (
        "|".join(sorted(res))
        + "\n"
        + str(len(info))
        + "\n"
        + "|".join(row.source for row in info)
        + "\n"
        + "|".join(row.generic for row in info)
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("%.17g" % statistics.median(elapsed))
