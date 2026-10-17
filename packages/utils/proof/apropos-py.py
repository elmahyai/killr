import statistics
import time

from utils.apropos import apropos
from utils.s3_session import BindingEnviron, attach


def one():
    return "\n".join(
        [
            "|".join(sorted(apropos("killrAproposProofGLM"))),
            "|".join(sorted(apropos("GLM", ignore_case=False))),
            str(len(apropos("GLM"))),
        ]
    )


env = BindingEnviron({"killrAproposProofGLM": 1})
attach(env, name="killrAproposProof", pos=2)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
