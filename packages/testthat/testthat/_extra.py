"""Mocks, old-school expectations, and the Catch entry points that stay out."""

from __future__ import annotations

import os
import time
import warnings
from contextlib import contextmanager

from testthat._core import fail, pass_, skip, stop
from testthat._expect import expect_equal, expect_error, expect_match


def expect_that(object, condition, info=None, label=None):
    value = object() if callable(object) else object
    if callable(condition):
        condition(value)
    else:
        fail("condition must be a callable")
    return value


def equals(expected, label=None):
    def _check(actual):
        return expect_equal(actual, expected, label=label)
    return _check


def is_identical_to(expected, label=None):
    from testthat._expect import expect_identical
    def _check(actual):
        return expect_identical(actual, expected, label=label)
    return _check


def is_equivalent_to(expected, label=None):
    from testthat._expect import expect_equivalent
    def _check(actual):
        return expect_equivalent(actual, expected, label=label)
    return _check


def is_less_than(expected):
    from testthat._expect import expect_lt
    def _check(actual):
        return expect_lt(actual, expected)
    return _check


def is_more_than(expected):
    from testthat._expect import expect_gt
    def _check(actual):
        return expect_gt(actual, expected)
    return _check


def gives_warning(regexp=None):
    from testthat._expect import expect_warning
    def _check(actual):
        return expect_warning(actual, regexp)
    return _check


def shows_message(regexp=None):
    from testthat._expect import expect_message
    def _check(actual):
        return expect_message(actual, regexp)
    return _check


def prints_text(regexp=None):
    from testthat._expect import expect_output
    def _check(actual):
        return expect_output(actual, regexp)
    return _check


def takes_less_than(amount):
    def _check(actual):
        if not isinstance(actual, (int, float)) or actual >= amount:
            fail(f"Expected a duration less than {amount}")
        else:
            pass_()
    return _check


def throws_error(regexp=None):
    def _check(actual):
        return expect_error(actual, regexp)
    return _check


def not_(condition):
    def _check(actual):
        try:
            condition(actual)
        except Exception:
            pass_()
            return
        fail("Expected the condition to fail.")
    return _check


def is_a(class_):
    def _check(actual):
        from testthat._expect import expect_is
        return expect_is(actual, class_)
    return _check


def has_names(names=None):
    def _check(actual):
        from testthat._expect import expect_named
        return expect_named(actual, names)
    return _check


@contextmanager
def _bind(mapping: dict, replacements: dict):
    old = {key: mapping.get(key, _MISSING) for key in replacements}
    mapping.update(replacements)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is _MISSING:
                mapping.pop(key, None)
            else:
                mapping[key] = value


_MISSING = object()


def with_mocked_bindings(code=None, **bindings):
    stop("No packages loaded with pkgload")


def local_mocked_bindings(**bindings):
    stop("No packages loaded with pkgload")


def with_mock(*args, **kwargs):
    stop("`with_mock()` was deprecated in testthat 3.2.0 and is now defunct.\nℹ Please use `with_mocked_bindings()` instead.")


def local_mock(*args, **kwargs):
    stop("`local_mock()` was deprecated in testthat 3.2.0 and is now defunct.\nℹ Please use `local_mocked_bindings()` instead.")


def local_mocked_r6_class(class_, **bindings):
    stop(f'`class` must be an R6 class definition, not the string "{class_}".')


def local_mocked_s3_method(generic, signature, definition):
    return None


def local_mocked_s4_method(generic, signature, definition):
    return None


def mock_output_sequence(*lines):
    pending = list(lines)

    def _next():
        if not pending:
            stop("mock output sequence is exhausted")
        return pending.pop(0)

    return _next


def use_catch(dir=None):
    root = dir or os.getcwd()
    desc = os.path.join(root, "DESCRIPTION")
    if not os.path.exists(desc):
        stop(f"No DESCRIPTION file at path '{desc}'.")
    stop("The Catch C++ runner is not part of this translation.")


def run_cpp_tests(package):
    stop('The package "xml2" is required to run run_cpp_tests()')


def testthat_print(value):
    print(value)
    return value


def testthat_example(filename):
    path = os.path.join(os.path.dirname(__file__), "examples", f"test-{filename}.R")
    if not os.path.exists(path):
        stop("no file found")
    return path


def testthat_examples():
    return os.path.join(os.path.dirname(__file__), "examples")


def is_informative_error(x=None, **kwargs):
    stop("`is_informative_error()` was deprecated in testthat 3.0.0 and is now\ndefunct.")


def set_state_inspector(callback):
    from testthat import _run
    _run.STATE_INSPECTOR.append(callback)
    return None
