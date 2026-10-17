import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "openssl_rsa_sign",
    Path(__file__).resolve().parents[1] / "openssl" / "rsa_sign.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
rsa_sign = _mod.rsa_sign

KEY_HEX = (
    "3082013b020100024100b4c90a4d2a92b08723b9c283c59ab0d337b773bcf76500ece62f856f86d3ad1e67e6da90c54008b7128d2f3330925229539cf8f220b8fa706864b6549e505813"
    "0203010001024047aed778d582a8a04d1820faa2e5bd6b62d249000a9070177f0624c09e135cb6e119b6252cec4196262f3d3322177142e3b5c549345a47ca33e63eae5ef7cd41"
    "022100d9d90e9e97920c28f6fb0ee34aa16cc7467a28fab4a875b24adf57a524d81a51"
    "022100d472541091cbb69607d0972d17130c2cbecf758f55ce285edfddbb528f1a0f23"
    "022026a89c2d8c9c40482cbc14c245062c75988e29238457b8bb310a3d55731a5e61"
    "022100cf787f8456fdbce833e58f5da7852084aa2b6c4178a8866070fbd7ae3eb65245"
    "0221008dc41791d6391f8c184e04bfc033862e4a3f0f513dfa2f998c0e7986b64fb929"
)
KEY = bytes.fromhex(KEY_HEX)


def one():
    sig = rsa_sign(bytes(range(1, 33)), KEY)
    return ",".join(str(b) for b in sig)


import statistics
import time

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
