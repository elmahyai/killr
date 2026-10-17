"""test_that and the file runners.

A test body is a callable. Helpers and package loading use importlib,
not pkgload.
"""

from __future__ import annotations

import importlib.util
import os
import traceback

from testthat._core import (
    STATE,
    Expectation,
    SkipSignal,
    TestthatError,
    handling,
    skip_empty,
    stop,
)
from testthat._reporter import (
    Reporter,
    StopReporter,
    get_reporter,
    with_reporter,
)


def test_that(desc: str, code):
    if not isinstance(desc, str) or not desc:
        stop("`desc` must be a single string")
    reporter = get_reporter()
    own = reporter is None
    if own:
        reporter = StopReporter()
    ok = True
    STATE.expectations = 0
    STATE.description.append(desc)
    STATE.in_test = True
    os.environ["TESTTHAT"] = "true"

    def on_exp(exp: Expectation):
        nonlocal ok
        if exp.kind in {"failure", "error"}:
            ok = False
        elif exp.kind == "skip":
            ok = False
        reporter.add_result(None, desc, exp)

    reporter.start_test(None, desc)
    try:
        with handling(on_exp):
            try:
                code() if callable(code) else None
                if STATE.expectations == 0 and ok:
                    # Expectations call pass_/fail which go through the handler
                    # but do not bump this counter unless we count deliveries.
                    pass
            except SkipSignal as skipped:
                ok = False
                reporter.add_result(None, desc, Expectation("skip", skipped.message))
            except Expectation as exp:
                ok = exp.kind not in {"failure", "error"}
                reporter.add_result(None, desc, exp)
            except TestthatError as exc:
                ok = False
                reporter.add_result(None, desc, Expectation("error", str(exc)))
            except Exception as exc:
                ok = False
                reporter.add_result(None, desc, Expectation("error", "".join(traceback.format_exception_only(type(exc), exc)).strip()))
        if not reporter.results and ok:
            try:
                skip_empty()
            except SkipSignal as skipped:
                ok = False
                reporter.add_result(None, desc, Expectation("skip", skipped.message))
    finally:
        STATE.description.pop()
        STATE.in_test = False
        reporter.end_test(None, desc)
        if own:
            reporter.end_reporter()
    return ok


def _count_success(reporter: Reporter) -> int:
    return sum(1 for item in reporter.results if item.kind == "success")


def test_file(path, reporter=None, load_helpers=True, desc=None, package=None, shuffle=False, **kwargs):
    if not os.path.exists(path):
        stop("`path` does not exist.")
    if str(path).endswith(".R"):
        stop(f"Can't run an R test file in the Python translation: {path}")
    chosen = reporter or StopReporter()
    namespace = {"__name__": "test_file"}
    with with_reporter(chosen):
        spec_text = open(path, encoding="utf-8").read()
        exec(compile(spec_text, path, "exec"), namespace, namespace)
    return _count_success(chosen)


def test_dir(path, reporter=None, load_helpers=True, desc=None, package=None, **kwargs):
    chosen = reporter or StopReporter()
    names = []
    if os.path.isdir(path):
        names = [name for name in sorted(os.listdir(path)) if name.startswith("test") and name.endswith(".py")]
    if not names:
        stop("No test files found.")
    total = 0
    for name in names:
        total += test_file(os.path.join(path, name), reporter=chosen, desc=desc)
    return total


def _description_error(path: str) -> None:
    stop(
        "Could not find a root 'DESCRIPTION' file that starts with '^Package' in\n"
        f"'{path}'.\n"
        "ℹ Are you in your project directory and does your project have a 'DESCRIPTION'\n"
        "  file?"
    )


def test_local(path=None, reporter=None, load_helpers=True, desc=None, **kwargs):
    root = path or os.getcwd()
    desc_path = os.path.join(root, "DESCRIPTION")
    if not os.path.isfile(desc_path):
        _description_error(root)
    tests = os.path.join(root, "tests", "testthat")
    if not os.path.isdir(tests):
        stop(f"Can't find {tests}")
    return test_dir(tests, reporter=reporter, desc=desc)


def test_package(package, reporter=None, **kwargs):
    print(f"No installed testthat tests found for {package}.")
    return None


def test_check(package, reporter=None, **kwargs):
    stop(f"Cannot find DESCRIPTION for installed package {package}")


def _package_dir(package: str) -> str:
    spec = importlib.util.find_spec(package)
    if spec is None or not spec.origin:
        stop(f"there is no package called ‘{package}’")
    return os.path.dirname(spec.origin)


def test_path(*parts):
    if STATE.in_test:
        base = ""
    else:
        base = os.path.join("tests", "testthat")
        if not os.path.isdir(base):
            stop("Can't find 'tests/testthat'.")
    bits = [base, *parts] if base else list(parts)
    return os.path.join(*bits) if bits else "."


def find_test_scripts(path, full_names=True, filter=None, invert=False, **kwargs):
    names = []
    if not os.path.isdir(path):
        return names
    for name in sorted(os.listdir(path)):
        if not (name.startswith("test") and (name.endswith(".py") or name.endswith(".R"))):
            continue
        if filter and (filter not in name) == (not invert):
            continue
        names.append(os.path.join(path, name) if full_names else name)
    return names


def source_file(path, env=None, chdir=True, wrap=True):
    if not os.path.exists(path):
        stop("`path` does not exist.")
    namespace = env if isinstance(env, dict) else {}
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), namespace, namespace)
    return namespace


def source_dir(path, pattern="test", env=None, chdir=True):
    loaded = []
    for name in sorted(os.listdir(path)):
        if pattern in name and name.endswith(".py"):
            loaded.append(source_file(os.path.join(path, name), env=env))
    return loaded


def source_test_helpers(path=None, env=None):
    root = path or os.path.join("tests", "testthat")
    return source_dir(root, pattern="helper", env=env)


def source_test_setup(path=None, env=None):
    root = path or os.path.join("tests", "testthat")
    return source_dir(root, pattern="setup", env=env)


def source_test_teardown(path=None, env=None):
    root = path or os.path.join("tests", "testthat")
    return source_dir(root, pattern="teardown", env=env)


def test_env(package=None):
    return {"package": package}


def setup(code=None, env=None):
    if callable(code):
        return code()
    return code


def teardown(code=None, env=None):
    return None


def teardown_env():
    stop(
        "`teardown_env()` has not been initialized.\n"
        "ℹ This is an internal error that was detected in the testthat package.\n"
        "  Please report it at <https://github.com/r-lib/testthat/issues> with a reprex\n"
        "  (<https://tidyverse.org/help/>) and the full backtrace."
    )


def simulate_test_env(package=None, path=None):
    if not isinstance(package, str) or not package:
        stop("`package` must be a single string, not absent.")
    if not isinstance(path, str) or not path:
        stop("`path` must be a single string, not absent.")
    return test_env(package)


def local_test_context():
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        old = os.environ.get("TESTTHAT")
        os.environ["TESTTHAT"] = "true"
        STATE.in_test = True
        try:
            yield
        finally:
            STATE.in_test = False
            if old is None:
                os.environ.pop("TESTTHAT", None)
            else:
                os.environ["TESTTHAT"] = old

    return _ctx()


def local_test_directory(path, package=None):
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        old = os.getcwd()
        os.chdir(path)
        STATE.package = package or ""
        try:
            yield
        finally:
            os.chdir(old)

    return _ctx()


def local_reproducible_output(width=80, crayon=False, unicode=False, rstudio=False, hyperlinks=False, lang="C"):
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        old_lang = os.environ.get("LANGUAGE")
        os.environ["LANGUAGE"] = lang
        if not rstudio:
            os.environ.pop("RSTUDIO", None)
        try:
            yield
        finally:
            if old_lang is None:
                os.environ.pop("LANGUAGE", None)
            else:
                os.environ["LANGUAGE"] = old_lang

    return _ctx()


def describe(description, code):
    return test_that(description, code)


def it(description, code=None):
    if code is None:
        from testthat._core import skip
        def _pending():
            skip(description)
        return test_that(description, _pending)
    return test_that(description, code)


def context(desc):
    if edition_get() >= 3:
        import warnings
        warnings.warn("context() was deprecated in the 3rd edition.", stacklevel=2)
    reporter = get_reporter()
    if reporter is not None:
        reporter.start_context(desc)
    return None


def context_start_file(name):
    return context(os.path.splitext(os.path.basename(name))[0])


def edition_get():
    from testthat._core import edition_get as _get
    return _get()


def try_again(times, code):
    last = None
    for _ in range(times):
        try:
            return code() if callable(code) else code
        except Exception as exc:
            last = exc
    if last is not None:
        raise last
    return None


def verify_output(path, code, width=80, crayon=False, unicode=False):
    from testthat._capture import capture_output
    from testthat._skip import on_cran, skip
    text = capture_output(code, print=True, width=width)
    if on_cran():
        skip("On CRAN")
    if not os.path.exists(path):
        open(path, "w", encoding="utf-8").write(text)
        return text
    old = open(path, encoding="utf-8").read()
    if old != text:
        stop("verify_output() file does not match the captured output.")
    return text


def test_example(path, reporter=None):
    """Run a Python example file. R example parsing is the evaluate package, which is not translated."""
    if not os.path.exists(path):
        stop("cannot open the connection")
    if str(path).endswith(".Rd") or str(path).endswith(".R"):
        stop("Could not find examples.")
    return test_file(path, reporter=reporter)


def test_examples(path=None):
    if path is None or not os.path.exists(path):
        stop("Could not find examples.")
    return test_example(path)


def test_rd(rd, package=None):
    stop("cannot open the connection")


def extract_test(location, path=None, package=""):
    pieces = str(location).split(":")
    if len(pieces) not in (2, 3):
        stop(f'Expected `location` to be of the form FILE:LINE[:COLUMN]\nℹ Got `location`: "{location}"')
    return location


def watch(path=None, callback=None):
    if path is None:
        stop('argument "path" is missing, with no default')
    stop("watch() needs a filesystem watcher, which is not part of this translation.")


def auto_test(code_path, test_path, reporter="summary"):
    if not os.path.exists(code_path) or not os.path.exists(test_path):
        stop("No test files found.")
    return test_dir(test_path)


def auto_test_package(package=None, reporter="summary"):
    _description_error(os.getcwd())


def set_state_inspector(callback):
    STATE_INSPECTOR.append(callback)
    return callback


STATE_INSPECTOR: list = []
