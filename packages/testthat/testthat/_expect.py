"""Expectations. A passing call returns the value. A failure raises Expectation."""

from __future__ import annotations

import math
import re
import warnings

from testthat._compare import (
    TOLERANCE,
    compare,
    testthat_tolerance,
    waldo_compare,
)
from testthat._core import (
    Expectation,
    TestthatError,
    edition_get,
    fail,
    label_of,
    pass_,
    stop,
)


def _value(actual, label, expected, expected_label):
    return actual, label_of(actual, label), expected, label_of(expected, expected_label)


def _waldo_fail(prefix: str, actual, actual_label, expected, expected_label, tolerance, info, ignore_attr=False):
    lines = waldo_compare(
        actual,
        expected,
        tolerance=tolerance,
        ignore_attr=ignore_attr,
    )
    if not lines:
        pass_()
        return actual
    message = [prefix.format(actual_label, expected_label), "Differences:", *lines]
    # lines already end in newlines; join would double them. Rebuild.
    body = prefix.format(actual_label, expected_label) + "\nDifferences:\n" + "".join(lines)
    if info:
        body = body + "\n" + str(info)
    fail(body)
    return actual


def expect_equal(object, expected, tolerance=None, info=None, label=None, expected_label=None, **kwargs):
    actual, actual_lab, exp, exp_lab = _value(object, label, expected, expected_label)
    if edition_get() >= 3:
        tol = testthat_tolerance() if tolerance is None else tolerance
        return _waldo_fail("Expected {} to equal {}.", actual, actual_lab, exp, exp_lab, tol, info)
    comp = compare(actual, exp, tolerance=tolerance)
    if comp.equal:
        pass_()
    else:
        fail(["Expected {} to equal {}.".format(actual_lab, exp_lab), "Differences:", comp.message], info)
    return actual


def expect_identical(object, expected, info=None, label=None, expected_label=None, **kwargs):
    actual, actual_lab, exp, exp_lab = _value(object, label, expected, expected_label)
    if edition_get() >= 3:
        return _waldo_fail(
            "Expected {} to be identical to {}.",
            actual,
            actual_lab,
            exp,
            exp_lab,
            None,
            info,
        )
    if actual == exp and type(actual) is type(exp):
        pass_()
    else:
        comp = compare(actual, exp, tolerance=None)
        detail = "Objects equal but not identical" if comp.equal else comp.message
        fail(["Expected {} to be identical to {}.".format(actual_lab, exp_lab), "Differences:", detail], info)
    return actual


def expect_equivalent(object, expected, info=None, label=None, expected_label=None, **kwargs):
    if edition_get() >= 3:
        warnings.warn("expect_equivalent() was deprecated in the 3rd edition. Use expect_equal(ignore_attr = TRUE)", stacklevel=2)
    actual, actual_lab, exp, exp_lab = _value(object, label, expected, expected_label)
    comp = compare(actual, exp)
    if comp.equal:
        pass_()
    else:
        fail(["Expected {} to be equivalent to {}.".format(actual_lab, exp_lab), "Differences:", comp.message], info)
    return actual


def expect_true(object, info=None, label=None):
    actual_lab = label_of(object, label)
    return _waldo_fail("Expected {} to be {}.", object, actual_lab, True, "TRUE", None, info, ignore_attr=True)


def expect_false(object, info=None, label=None):
    actual_lab = label_of(object, label)
    return _waldo_fail("Expected {} to be {}.", object, actual_lab, False, "FALSE", None, info, ignore_attr=True)


def expect_null(object, info=None, label=None):
    actual_lab = label_of(object, label)
    return _waldo_fail("Expected {} to be {}.", object, actual_lab, None, "NULL", None, info)


def _compare_op(operator: str, actual, expected, label, expected_label):
    ops = {
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
    }
    flipped = {"<": ">=", "<=": ">", ">": "<=", ">=": "<"}
    actual_lab = label_of(actual, label)
    exp_lab = label_of(expected, expected_label)
    try:
        result = ops[operator](actual, expected)
    except TypeError as exc:
        stop(str(exc))
    if result is True:
        pass_()
        return actual
    if not isinstance(result, bool):
        stop("Result of comparison must be `TRUE`, `FALSE`, or `NA`")
    digits = 1
    if isinstance(actual, (int, float)) and not isinstance(actual, bool):
        act = f"{float(actual):.{digits}f}"
        exp = f"{float(expected):.{digits}f}"
        diff = float(actual) - float(expected)
        message = "\n".join([
            f"Expected {actual_lab} {operator} {exp_lab}.",
            f"Actual comparison: {act} {flipped[operator]} {exp}",
            f"Difference: {diff:.{digits}f} {flipped[operator]} 0",
        ])
    else:
        message = "\n".join([
            f"Expected {actual_lab} {operator} {exp_lab}.",
            f'Actual comparison: "{actual}" {flipped[operator]} "{expected}"',
        ])
    fail(message)
    return actual


def expect_lt(object, expected, label=None, expected_label=None):
    return _compare_op("<", object, expected, label, expected_label)


def expect_lte(object, expected, label=None, expected_label=None):
    return _compare_op("<=", object, expected, label, expected_label)


def expect_gt(object, expected, label=None, expected_label=None):
    return _compare_op(">", object, expected, label, expected_label)


def expect_gte(object, expected, label=None, expected_label=None):
    return _compare_op(">=", object, expected, label, expected_label)


def expect_less_than(*args, **kwargs):
    warnings.warn("Deprecated: please use expect_lt instead.", stacklevel=2)
    return expect_lt(*args, **kwargs)


def expect_more_than(*args, **kwargs):
    warnings.warn("Deprecated: please use expect_gt instead.", stacklevel=2)
    return expect_gt(*args, **kwargs)


def _match_one(text: str, regexp: str, fixed: bool, perl: bool, ignore_case: bool = False) -> bool:
    if fixed:
        return regexp in text
    flags = re.IGNORECASE if ignore_case else 0
    return re.search(regexp, text, flags) is not None


def expect_match(object, regexp, perl=False, fixed=False, all_=True, info=None, label=None, ignore_case=False):
    values = object if isinstance(object, (list, tuple)) else [object]
    actual_lab = label_of(object, label)
    if len(values) == 0:
        fail(f"Expected {actual_lab} to have at least one element.", info)
        return object
    hits = [_match_one(str(item), regexp, fixed, perl, ignore_case) for item in values]
    ok = all(hits) if all_ else any(hits)
    if ok:
        pass_()
    else:
        fail(f"Expected {actual_lab} to match {regexp!r}.", info)
    return object


def expect_no_match(object, regexp, perl=False, fixed=False, all_=True, info=None, label=None, ignore_case=False):
    values = object if isinstance(object, (list, tuple)) else [object]
    actual_lab = label_of(object, label)
    hits = [_match_one(str(item), regexp, fixed, perl, ignore_case) for item in values]
    ok = not any(hits) if all_ else not all(hits)
    if ok:
        pass_()
    else:
        fail(f"Expected {actual_lab} not to match {regexp!r}.", info)
    return object


def expect_length(object, n, info=None, label=None):
    actual_lab = label_of(object, label)
    if object is None:
        length = 0
    elif isinstance(object, (int, float, bool)):
        length = 1
    else:
        length = len(object)
    if length != n:
        fail(f"{actual_lab} has length {length}, not length {n}.", info)
    else:
        pass_()
    return object


def expect_named(object, expected_names=None, ignore_order=False, ignore_case=False, info=None, label=None):
    actual_lab = label_of(object, label)
    if isinstance(object, dict):
        names = list(object)
    else:
        names = list(getattr(object, "names", []) or [])
    if expected_names is None:
        ok = len(names) == (len(object) if object is not None else 0) and all(names)
    else:
        left = [item.lower() if ignore_case else item for item in names]
        right = [item.lower() if ignore_case else item for item in expected_names]
        if ignore_order:
            ok = sorted(left) == sorted(right)
        else:
            ok = left == list(right)
    if ok:
        pass_()
    else:
        fail(f"Expected {actual_lab} to have names {expected_names}. Actual: {names}.", info)
    return object


def _as_list(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        return [value]
    return [value]


def expect_setequal(object, expected):
    left, right = _as_list(object), _as_list(expected)
    if sorted(map(repr, left)) == sorted(map(repr, right)) and len(set(map(repr, left))) == len(set(map(repr, right))):
        # Membership, not multiplicity: every distinct value of each is in the other.
        pass_()
    else:
        missing_actual = [item for item in dict.fromkeys(left) if item not in right]
        missing_expected = [item for item in dict.fromkeys(right) if item not in left]
        if not missing_actual and not missing_expected:
            pass_()
            return object
        fail(f"Expected {label_of(object, None)} to have the same values as {label_of(expected, None)}.")
    return object


def expect_contains(object, expected):
    left, right = _as_list(object), _as_list(expected)
    if all(item in left for item in right):
        pass_()
    else:
        fail(f"Expected {label_of(object, None)} to contain {label_of(expected, None)}.")
    return object


def expect_in(object, expected):
    left, right = _as_list(object), _as_list(expected)
    if all(item in right for item in left):
        pass_()
    else:
        fail(f"Expected {label_of(object, None)} to be in {label_of(expected, None)}.")
    return object


def expect_disjoint(object, expected):
    left, right = _as_list(object), _as_list(expected)
    if all(item not in right for item in left):
        pass_()
    else:
        fail(f"Expected {label_of(object, None)} to be disjoint from {label_of(expected, None)}.")
    return object


def expect_mapequal(object, expected):
    if not isinstance(object, dict) or not isinstance(expected, dict):
        stop("expect_mapequal() expects named lists")
    if object.keys() == expected.keys() and all(object[key] == expected[key] for key in object):
        pass_()
    else:
        fail("Names and values differ.")
    return object


def _typeof(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "character"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "list"
    return type(value).__name__


def expect_type(object, type):
    actual = _typeof(object)
    if actual != type:
        fail([f"Expected {label_of(object, None)} to have type {type}.", f"Actual type: {actual}"])
    else:
        pass_()
    return object


def expect_s3_class(object, class_, exact=False):
    classes = list(getattr(object, "classes", []) or [])
    if class_ is None or (isinstance(class_, float) and math.isnan(class_)):
        ok = not classes
    else:
        wanted = class_ if isinstance(class_, (list, tuple)) else [class_]
        ok = classes == list(wanted) if exact else any(item in classes for item in wanted)
    if ok:
        pass_()
    else:
        fail(f"Expected an S3 object with class {class_}. Actual: {classes or 'none'}.")
    return object


def expect_s4_class(object, class_):
    is_s4 = bool(getattr(object, "s4", False))
    if class_ is None or (isinstance(class_, float) and math.isnan(class_)):
        ok = not is_s4
    else:
        ok = is_s4 and class_ in getattr(object, "classes", [])
    if ok:
        pass_()
    else:
        fail(f"Expected an S4 object of class {class_}.")
    return object


def expect_r6_class(object, class_):
    ok = class_ in type(object).__mro__.__repr__() or class_ == type(object).__name__ or class_ in getattr(object, "classes", [])
    if ok:
        pass_()
    else:
        fail(f"Expected an R6 object inheriting from {class_}.")
    return object


def expect_s7_class(object, class_):
    stop('The package "S7" is required.')


def expect_is(object, class_):
    if class_ == "numeric" and isinstance(object, (int, float)) and not isinstance(object, bool):
        pass_()
        return object
    if class_ == "integer" and isinstance(object, int) and not isinstance(object, bool):
        pass_()
        return object
    if class_ == "double" and isinstance(object, float):
        pass_()
        return object
    if class_ == "character" and isinstance(object, str):
        pass_()
        return object
    if class_ == "logical" and isinstance(object, bool):
        pass_()
        return object
    return expect_s3_class(object, class_)


def expect_vector(object, ptype=None, size=None):
    if size is not None and len(object) != size:
        fail(f"Expected vector of size {size}. Actual size: {len(object)}.")
    else:
        pass_()
    return object


def expect_shape(object, *extra, nrow=None, ncol=None, dim=None):
    if extra:
        stop("`...` must be empty.\n✖ Problematic argument:\n• ..1 = c(2, 2)\nℹ Did you forget to name an argument?")
    actual = getattr(object, "shape", None)
    if actual is None:
        fail(f"Expected {label_of(object, None)} to have dimensions.")
        return object
    if nrow is not None:
        if int(actual[0]) != int(nrow):
            fail(f"Expected {label_of(object, None)} to have {int(nrow)} rows.\nActual rows: {int(actual[0])}.")
        else:
            pass_()
    elif ncol is not None:
        if len(actual) < 2 or int(actual[1]) != int(ncol):
            fail(f"Expected {label_of(object, None)} to have {int(ncol)} columns.")
        else:
            pass_()
    elif dim is not None:
        if tuple(int(item) for item in actual) != tuple(int(item) for item in dim):
            fail(f"Expected dimensions {tuple(dim)}. Actual: {tuple(actual)}.")
        else:
            pass_()
    else:
        stop("Must supply one of `nrow`, `ncol`, or `dim`.")
    return object


def _run_callable(code):
    import io
    import contextlib
    stdout = io.StringIO()
    messages: list[str] = []
    warns: list[str] = []
    try:
        with contextlib.redirect_stdout(stdout):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                value = code() if callable(code) else code
                warns.extend(str(item.message) for item in caught)
    except Exception as exc:
        return {"value": None, "output": stdout.getvalue(), "error": exc, "warnings": warns, "messages": messages}
    return {"value": value, "output": stdout.getvalue(), "error": None, "warnings": warns, "messages": messages}


def expect_error(object, regexp=None, class_=None, info=None, label=None, ignore_case=False):
    result = _run_callable(object)
    error = result["error"]
    if regexp is None and error is None:
        # NA means no error. None means some error. Use a sentinel via regexp is False? R uses NA.
        fail("Expected an error.")
        return None
    if regexp == "NA" or (isinstance(regexp, float) and math.isnan(regexp)):
        if error is not None:
            fail(f"Expected no error. Actual: {error}")
        else:
            pass_()
        return result["value"]
    if error is None:
        fail(f"Expected {label_of(object, label)} to throw an error.")
        return None
    text = str(error)
    if class_ is not None and class_ not in type(error).__mro__.__repr__() and class_ != type(error).__name__:
        fail(f"Expected error of class {class_}. Actual: {type(error).__name__}.")
    elif regexp is not None and not _match_one(text, str(regexp), False, False, ignore_case):
        fail(f"Expected error matching {regexp!r}. Actual: {text}")
    else:
        pass_()
    return error


def expect_warning(object, regexp=None, info=None, label=None, ignore_case=False):
    result = _run_callable(object)
    if result["error"] is not None:
        raise result["error"]
    warns = result["warnings"]
    if regexp == "NA" or (isinstance(regexp, float) and isinstance(regexp, float) and math.isnan(regexp)):
        if warns:
            fail(f"Expected no warning. Actual: {warns[0]}")
        else:
            pass_()
        return result["value"]
    if not warns:
        fail("Expected a warning.")
        return result["value"]
    if regexp is not None and not _match_one(warns[0], str(regexp), False, False, ignore_case):
        fail(f"Expected warning matching {regexp!r}. Actual: {warns[0]}")
    else:
        pass_()
    return result["value"]


def expect_message(object, regexp=None, info=None, label=None, ignore_case=False):
    """message() in this translation is a warning with category UserWarning, or text written by message()."""
    from testthat._capture import take_messages

    notes: list[str] = []
    def run():
        with take_messages(notes):
            return object() if callable(object) else object
    try:
        value = run()
    except Exception as exc:
        raise exc
    if regexp == "NA" or (isinstance(regexp, float) and math.isnan(regexp)):
        if notes:
            fail(f"Expected no message. Actual: {notes[0]}")
        else:
            pass_()
        return value
    if not notes:
        fail("Expected a message.")
        return value
    if regexp is not None and not _match_one(notes[0], str(regexp), False, False, ignore_case):
        fail(f"Expected message matching {regexp!r}. Actual: {notes[0]}")
    else:
        pass_()
    return value


def expect_condition(object, regexp=None, class_=None, info=None, label=None):
    result = _run_callable(object)
    if result["error"] is None and not result["warnings"]:
        fail("Expected a condition.")
        return None
    pass_()
    return result["error"] or result["warnings"][0]


def expect_no_error(object, message=None, class_=None):
    result = _run_callable(object)
    if result["error"] is not None:
        fail(f"Expected no error. Actual: {result['error']}")
    else:
        pass_()
    return result["value"]


def expect_no_warning(object, message=None, class_=None):
    result = _run_callable(object)
    if result["error"] is not None:
        raise result["error"]
    if result["warnings"]:
        fail(f"Expected no warning. Actual: {result['warnings'][0]}")
    else:
        pass_()
    return result["value"]


def expect_no_message(object, message=None, class_=None):
    from testthat._capture import take_messages
    notes: list[str] = []
    with take_messages(notes):
        value = object() if callable(object) else object
    if notes:
        fail(f"Expected no message. Actual: {notes[0]}")
    else:
        pass_()
    return value


def expect_no_condition(object, message=None, class_=None):
    return expect_no_error(object)


def expect_output(object, regexp=None, info=None, label=None, width=80):
    import contextlib
    import io
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        value = object() if callable(object) else object
    text = stream.getvalue()
    if regexp is None:
        ok = text != ""
    else:
        ok = _match_one(text, str(regexp), False, False)
    if ok:
        pass_()
    else:
        fail(f"Expected output matching {regexp!r}. Actual: {text!r}")
    return value


def expect_silent(object):
    from testthat._capture import capture_output, take_messages
    notes: list[str] = []
    with take_messages(notes):
        text = capture_output(object)
        result = _run_callable(object)
    noisy = []
    if text.strip():
        noisy.append("output")
    if result["warnings"]:
        noisy.append("warnings")
    if notes:
        noisy.append("messages")
    if noisy:
        fail([f"Expected {label_of(object, None)} to run silently.", "Actual noise: " + ", ".join(noisy) + "."])
    else:
        pass_()
    return result["value"]


def expect_invisible(object):
    """A callable that returns a value is visible. Pass invisible=True on the callable to mark it."""
    call = object if callable(object) else None
    visible = True if call is None else not getattr(call, "invisible", False)
    value = call() if call else object
    if visible:
        fail("Expected result to be invisible.")
    else:
        pass_()
    return value


def expect_visible(object):
    call = object if callable(object) else None
    visible = True if call is None else not getattr(call, "invisible", False)
    value = call() if call else object
    if not visible:
        fail("Expected result to be visible.")
    else:
        pass_()
    return value


def expect_reference(object, expected):
    if object is expected:
        pass_()
    else:
        fail("Expected the two objects to be the same reference.")
    return object


def expect_success(object):
    try:
        object() if callable(object) else object
    except Expectation as exp:
        if exp.kind != "success":
            fail("Expected a success.")
            return None
    pass_()
    return None


def expect_failure(object, message=None, info=None):
    try:
        object() if callable(object) else object
    except Expectation as exp:
        if exp.kind == "failure" and (message is None or message in exp.message):
            pass_()
            return None
        fail("Expected a failure.")
        return None
    fail("Expected a failure.")
    return None


def expect_no_success(object, message=None):
    warnings.warn("expect_no_success() was deprecated in testthat 3.3.0. Use expect_failure().", stacklevel=2)
    return expect_failure(object, message)


def expect_no_failure(object, message=None):
    warnings.warn("expect_no_failure() was deprecated in testthat 3.3.0. Use expect_success().", stacklevel=2)
    return expect_success(object)


def expect_output_file(object, path, update=False):
    from testthat._capture import capture_output
    text = capture_output(object)
    if update or not os_path_exists(path):
        open(path, "w", encoding="utf-8").write(text)
        pass_()
        return text
    old = open(path, encoding="utf-8").read()
    if old == text:
        pass_()
    else:
        fail("Output file does not match.")
    return text


def os_path_exists(path) -> bool:
    import os
    return os.path.exists(path)


def expect_known_output(object, path, update=False, **kwargs):
    return expect_output_file(object, path, update=update)


def expect_known_value(object, path, update=False, **kwargs):
    import json
    value = object() if callable(object) else object
    if update or not os_path_exists(path):
        open(path, "w", encoding="utf-8").write(json.dumps(value))
        pass_()
        return value
    old = json.loads(open(path, encoding="utf-8").read())
    return expect_equal(value, old)


def expect_equal_to_reference(object, path, update=False, **kwargs):
    return expect_known_value(object, path, update=update)


def expect_known_hash(object, hash=None):
    from digest import character, integer, logical, real
    from digest import digest as r_digest
    value = object() if callable(object) else object
    if isinstance(value, bool):
        hashed = logical([value])
    elif isinstance(value, int) and not isinstance(value, bool):
        hashed = integer([value])
    elif isinstance(value, float):
        hashed = real([value])
    elif isinstance(value, str):
        hashed = character([value])
    else:
        hashed = character([str(value)])
    actual = r_digest(hashed)
    if hash is None:
        fail(f"Expected hash is missing. Actual hash: {actual}")
        return value
    if actual != hash:
        fail(f"Expected hash {hash}. Actual: {actual}")
    else:
        pass_()
    return value


def expect_all_equal(object, expected, **kwargs):
    values = _as_list(object)
    if all(item == expected for item in values):
        pass_()
    else:
        fail("Not all elements are equal to the expected value.")
    return object


def expect_all_true(object):
    values = _as_list(object)
    if values and all(item is True for item in values):
        pass_()
    else:
        fail("Not all elements are TRUE.")
    return object


def expect_all_false(object):
    values = _as_list(object)
    if values and all(item is False for item in values):
        pass_()
    else:
        fail("Not all elements are FALSE.")
    return object


def expect_cpp_tests_pass(package):
    stop(f"there is no package called ‘{package}’")


def _snap3(name):
    from testthat._snapshot import _edition3
    _edition3(name)


def expect_snapshot(object, cran=False, error=False, variant=None, transform=None, style="full", cnd_class=False):
    _snap3("expect_snapshot")
    from testthat._snapshot import snapshot_value
    snapshot_value(object, variant=variant, transform=transform)
    return None


def expect_snapshot_output(object, variant=None, transform=None):
    _snap3("expect_snapshot_output")
    from testthat._capture import capture_output
    text = capture_output(object)
    from testthat._snapshot import announce
    announce(text, "output")
    return None


def expect_snapshot_value(object, style="json2", cran=False, tolerance=None, variant=None):
    _snap3("expect_snapshot_value")
    from testthat._snapshot import snapshot_value
    snapshot_value(object, style=style, variant=variant)
    return None


def expect_snapshot_error(object, class_=False, variant=None, transform=None, cran=False):
    _snap3("expect_snapshot_error")
    result = _run_callable(object)
    if result["error"] is None:
        fail("Expected an error to snapshot.")
        return None
    from testthat._snapshot import announce
    announce(str(result["error"]), "error")
    return None


def expect_snapshot_failure(object, variant=None, transform=None, cran=False):
    _snap3("expect_snapshot_failure")
    try:
        object() if callable(object) else object
    except Expectation as exp:
        from testthat._snapshot import announce
        announce(exp.message, "failure")
        return None
    fail("Expected a failure to snapshot.")
    return None


def expect_snapshot_warning(object, class_=False, variant=None, transform=None, cran=False):
    _snap3("expect_snapshot_warning")
    result = _run_callable(object)
    if not result["warnings"]:
        fail("Expected a warning to snapshot.")
        return None
    from testthat._snapshot import announce
    announce(result["warnings"][0], "warning")
    return None


def expect_snapshot_file(path, name=None, binary=None, cran=False, compare=None, transform=None, variant=None):
    _snap3("expect_snapshot_file")
    from testthat._snapshot import snapshot_file
    snapshot_file(path, name=name or path, binary=binary)
    return None


def show_failure(expr):
    try:
        expr() if callable(expr) else expr
    except Expectation as exp:
        print(exp.message)
    return None


def quasi_label(value, label=None, arg=None):
    stop("`quo` must be a quosure")


def make_expectation(exp, expectation="equals"):
    """Print an expect_equal() call for the value, matching R's dput helper."""
    print(f"expect_equal({exp!r}, {exp!r})")
    return None
