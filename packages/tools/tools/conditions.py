"""Condition assertions from tools 4.5.0."""

import warnings


def _classes_of(kind):
    if kind == "error":
        return ["simpleError", "error", "condition"]
    return ["simpleWarning", "warning", "condition"]


def _collect(action):
    found = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            action()
        except Exception as exc:
            for item in caught:
                found.append({"class": _classes_of("warning"), "message": str(item.message)})
            found.append({"class": _classes_of("error"), "message": str(exc)})
        else:
            for item in caught:
                found.append({"class": _classes_of("warning"), "message": str(item.message)})
    return found


def _wanted(classes):
    names = [item for item in classes if item is not None]
    if not names:
        return "any condition"
    return " or ".join(names)


def _quote(text):
    return f"\u201c{text}\u201d"


def assert_condition(action, *classes, expr_string="expr", verbose=False):
    """Run action and require one of the condition classes."""
    wanted = _wanted(classes)
    found = _collect(action)
    if not found:
        raise ValueError(f"Failed to get {wanted} in evaluating {expr_string}")
    if not classes:
        if verbose:
            print("assertConditon: successfully caught a condition")
        return found
    matched = []
    for cond in found:
        if any(name in classes for name in cond["class"]):
            matched.append(cond)
    if matched:
        if verbose:
            names = []
            for cond in matched:
                for name in cond["class"]:
                    if name in classes and name not in names:
                        names.append(name)
            print("assertCondition: caught " + ", ".join(_quote(name) for name in names))
        return found
    got = []
    for cond in found:
        name = cond["class"][0]
        if name not in got:
            got.append(name)
    raise ValueError(
        f"Got {', '.join(got)} in evaluating {expr_string}; wanted {wanted}"
    )


def assert_error(action, classes="error", verbose=False, expr_string="expr"):
    """Require action to signal an error."""
    if isinstance(classes, str):
        classes = [classes]
    try:
        found = assert_condition(action, *classes, expr_string=expr_string, verbose=False)
    except Exception:
        raise ValueError(f"Failed to get error in evaluating {expr_string}") from None
    if verbose:
        for cond in found:
            if any(name in classes for name in cond["class"]):
                print(f"Asserted error: {cond['message']}")
                break
    return found


def assert_warning(action, classes="warning", verbose=False, expr_string="expr"):
    """Require action to signal a warning and not an error."""
    if isinstance(classes, str):
        classes = [classes]
    found = assert_condition(action, *classes, expr_string=expr_string, verbose=False)
    if any("error" in cond["class"] for cond in found):
        raise ValueError(f"Got warning in evaluating {expr_string}, but also an error")
    if verbose:
        for cond in found:
            if any(name in classes for name in cond["class"]):
                print(f"Asserted warning: {cond['message']}")
                break
    return found
