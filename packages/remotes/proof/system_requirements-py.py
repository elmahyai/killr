import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remotes.system_requirements import system_requirements

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)

OS_MSG = (
    "'arg' should be one of \u201cubuntu\u201d, \u201ccentos\u201d, "
    "\u201credhat\u201d, \u201copensuse\u201d, \u201csle\u201d"
)
UB_MSG = (
    "'arg' should be one of \u201c14.04\u201d, \u201c16.04\u201d, "
    "\u201c18.04\u201d, \u201c20.04\u201d, \u201c22.04\u201d"
)
CURL_MSG = "`curl` must be on the `PATH`."
SPLIT_MSG = "If os_release is missing, os must consist of name and release."


def expect_error(fn, expected: str) -> None:
    try:
        fn()
    except RuntimeError as exc:
        got = str(exc)
    else:
        raise AssertionError(f"expected {expected!r}")
    if got != expected:
        raise AssertionError(f"expected {expected!r} got {got!r}")


expect_error(lambda: system_requirements("foo", "1"), OS_MSG)
expect_error(lambda: system_requirements("ubuntu", "1"), UB_MSG)
expect_error(lambda: system_requirements("ubuntu", "2"), UB_MSG)
expect_error(lambda: system_requirements("ubuntu"), SPLIT_MSG)
expect_error(lambda: system_requirements("ubuntu-"), SPLIT_MSG)
expect_error(lambda: system_requirements("ubuntu-16.04-extra"), SPLIT_MSG)
expect_error(lambda: system_requirements("-16.04"), OS_MSG)
expect_error(lambda: system_requirements("foo-bar"), OS_MSG)
expect_error(lambda: system_requirements("ubuntu", "16.04", curl=""), CURL_MSG)
expect_error(lambda: system_requirements("foo", "1", curl=""), OS_MSG)
expect_error(lambda: system_requirements("u", "16", curl=""), CURL_MSG)
expect_error(lambda: system_requirements("ubuntu-16.04", curl=""), CURL_MSG)
expect_error(
    lambda: system_requirements("ubuntu", "16.04", "not-a-package-dir"),
    "`not-a-package-dir` must contain a package.",
)


def make_pkg(text: str) -> str:
    directory = tempfile.mkdtemp()
    with open(os.path.join(directory, "DESCRIPTION"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text if text.endswith("\n") else text + "\n")
    return directory


lib = make_pkg("Package: testPkg\nSystemRequirements: libcurl")
empty = make_pkg("Package: testPkg")
bad = make_pkg("Not parsable")


def one():
    return system_requirements("ubuntu", "16.04", lib)


value = one()
assert value == ["apt-get install -y libcurl4-openssl-dev"]
assert system_requirements("redhat", "7", lib) == ["yum install -y libcurl-devel"]
assert system_requirements("ubuntu", "16.04", empty) == []
expect_error(
    lambda: system_requirements("ubuntu", "16.04", bad),
    "Could not parse DESCRIPTION: Bad line: 'Not parsable\\n' has no ':'",
)

sentence = (
    'system_requirements("ubuntu", "16.04") for SystemRequirements: libcurl returns '
    f'"{value[0]}".'
)
(out_dir / "system_requirements-python.txt").write_text(sentence + "\n", encoding="utf-8")

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    got = one()
    elapsed.append((time.perf_counter() - started) * 1000)
    assert got == value

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
