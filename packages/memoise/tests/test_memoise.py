import tempfile
from pathlib import Path

import pytest

from memoise import (
    cache_filesystem,
    cache_gcs,
    cache_memory,
    cache_s3,
    drop_cache,
    forget,
    has_cache,
    is_memoised,
    is_memoized,
    memoise,
    memoize,
    timeout,
)


def test_repeat_call_runs_once_and_defaults_hit():
    calls = {"n": 0}

    def f(x, dummy="a"):
        calls["n"] += 1
        return x + len(dummy)

    memo = memoise(f)
    assert [memo(2), memo(2), memo(2, dummy="a"), calls["n"]] == [3, 3, 3, 1]
    assert memo(2, dummy="b") == 3
    assert calls["n"] == 2
    assert memo(dummy="b", x=2) == 3
    assert calls["n"] == 2


def test_memoize_alias_and_reject_double_wrap():
    calls = {"n": 0}

    def f(x):
        calls["n"] += 1
        return x + 3

    memo = memoize(f)
    assert memo(2) == 5
    assert memo(2) == 5
    assert calls["n"] == 1
    with pytest.raises(ValueError, match="must not be memoised"):
        memoise(memo)


def test_forget_clears_and_plain_function_is_false():
    calls = {"n": 0}

    def f(x):
        calls["n"] += 1
        return x

    assert forget(f) is False
    memo = memoise(f)
    assert memo(1) == 1
    assert forget(memo) is True
    assert memo(1) == 1
    assert calls["n"] == 2


def test_has_cache_and_drop_cache():
    memo = memoise(lambda x: x)
    assert has_cache(memo)(1) is False
    memo(1)
    memo(2)
    assert has_cache(memo)(1) is True
    assert drop_cache(memo)(1) is True
    assert has_cache(memo)(1) is False
    assert has_cache(memo)(2) is True
    assert drop_cache(memo)(1) is False
    with pytest.raises(ValueError, match="not a memoised"):
        has_cache(lambda x: x)


def test_is_memoised_names():
    def f(x):
        return x

    memo = memoise(f)
    assert is_memoised(f) is False
    assert is_memoised(memo) is True
    assert is_memoized(memo) is True


def test_timeout_bucket_and_extra_callable():
    assert timeout(10, current=25) == 2
    assert timeout(10, current=30) == 3
    calls = {"n": 0}

    def f(x):
        calls["n"] += 1
        return x

    clock = {"t": 100}
    memo = memoise(f, lambda: timeout(10, current=clock["t"]))
    assert memo(1) == 1
    assert memo(1) == 1
    clock["t"] = 111
    assert memo(1) == 1
    assert calls["n"] == 2


def test_omit_args_ignores_named_value():
    calls = {"n": 0}

    def f(x, dummy="a"):
        calls["n"] += 1
        return (x, dummy)

    memo = memoise(f, omit_args="dummy")
    assert memo(3, dummy="a") == (3, "a")
    assert memo(3, dummy="z") == (3, "a")
    assert calls["n"] == 1


def test_old_memory_cache_and_filesystem_roundtrip():
    calls = {"n": 0}

    def f(x):
        calls["n"] += 1
        return calls["n"]

    store = cache_memory()
    memo = memoise(f, cache=store)
    assert memo(1) == 1
    assert memo(1) == 1
    assert calls["n"] == 1

    store.set("k", 7)
    assert store.get("k") == 7
    assert store.has_key("k") is True
    store.drop_key("k")
    assert store.has_key("k") is False
    store.set("a", 1)
    store.reset()
    assert store.keys() == []

    with tempfile.TemporaryDirectory() as folder:
        disk = cache_filesystem(folder)
        disk.set("abc", 4)
        assert disk.get("abc") == 4
        assert disk.has_key("abc") is True
        disk.drop_key("abc")
        assert disk.has_key("abc") is False
        disk.set("a", 1)
        disk.reset()
        assert disk.keys() == []

        gzipped = cache_filesystem(Path(folder) / "gz", compress="gzip")
        gzipped.set("z", [1, 2, 3])
        assert gzipped.get("z") == [1, 2, 3]


def test_shared_cache_is_independent_per_function_hash():
    shared = cache_memory()
    first = memoise(lambda x: x + 1, cache=shared)
    second = memoise(lambda x: x + 10, cache=shared)
    assert first(1) == 2
    assert second(1) == 11


def _ready(module: str) -> dict:
    import json
    import subprocess
    import sys
    import time
    from pathlib import Path

    ready = Path(tempfile.mktemp(prefix=f"{module}-"))
    subprocess.Popen(
        [sys.executable, "-m", module, str(ready)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        if ready.exists() and ready.stat().st_size:
            return json.loads(ready.read_text())
        time.sleep(0.05)
    raise RuntimeError(f"{module} did not start")


def test_cache_s3_roundtrip(monkeypatch):
    info = _ready("memoise._s3mock")
    monkeypatch.setenv("AWS_S3_ENDPOINT", f"127.0.0.1:{info['port']}")
    monkeypatch.setenv("SSL_CERT_FILE", info["cert"])
    monkeypatch.setenv("CURL_CA_BUNDLE", info["cert"])
    store = cache_s3("bkt12345678")
    store.set("abc", 4)
    assert store.get("abc") == 4
    assert store.has_key("abc") is True
    assert store.keys() == ["abc"]
    store.drop_key("abc")
    assert store.has_key("abc") is False


def test_cache_gcs_roundtrip(monkeypatch):
    info = _ready("memoise._gcsmock")
    monkeypatch.setenv("GCS_API_HOST", f"127.0.0.1:{info['port']}")
    monkeypatch.setenv("SSL_CERT_FILE", info["cert"])
    monkeypatch.setenv("CURL_CA_BUNDLE", info["cert"])
    store = cache_gcs("local-bucket")
    store.set("abc", 4)
    store.set("zzz", 1)
    assert store.get("abc") == 4
    assert store.has_key("abc") is True
    store.drop_key("abc")
    assert store.has_key("abc") is False
    assert store.get("zzz") == 1
    assert store.keys() == ["zzz"]
