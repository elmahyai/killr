from lifecycle import (
    LifecycleError,
    lifecycle_linter,
    lint_lifecycle,
    lint_tidyverse_lifecycle,
    pkg_lifecycle_statuses,
)


def test_lifecycle_package_rows():
    rows = pkg_lifecycle_statuses("lifecycle")
    assert [(row["fun"], row["lifecycle"]) for row in rows] == [
        ("badge", "experimental"),
        ("signal_experimental", "deprecated"),
        ("signal_superseded", "deprecated"),
        ("signal_stage", "experimental"),
    ]
    assert {row["package"] for row in rows} == {"lifecycle"}


def test_stringr_superseded_interp():
    rows = pkg_lifecycle_statuses("stringr")
    assert [(row["fun"], row["lifecycle"]) for row in rows] == [("str_interp", "superseded")]


def test_which_drops_na_and_can_be_empty():
    deprecated = pkg_lifecycle_statuses("lifecycle", which=["deprecated", None])
    assert [row["fun"] for row in deprecated] == ["signal_experimental", "signal_superseded"]
    assert pkg_lifecycle_statuses("lifecycle", which="questioning") == []


def test_status_errors():
    try:
        pkg_lifecycle_statuses(1)
    except LifecycleError as exc:
        assert str(exc) == "is_string(package) is not TRUE"
    else:
        raise AssertionError("expected a string check")
    try:
        pkg_lifecycle_statuses("not_a_real_pkg_zz")
    except LifecycleError as exc:
        assert str(exc) == "there is no package called \u2018not_a_real_pkg_zz\u2019"
    else:
        raise AssertionError("expected a missing package")


def test_linters_report_the_missing_r_packages():
    pair = 'The packages "lintr" and "xml2" are required.'
    trio = 'The packages "lintr", "xml2", and "tidyverse" are required.'
    for call in (lifecycle_linter, lambda: lint_lifecycle("lifecycle")):
        try:
            call()
        except LifecycleError as exc:
            assert str(exc) == pair
        else:
            raise AssertionError("expected the lintr error")
    try:
        lint_tidyverse_lifecycle()
    except LifecycleError as exc:
        assert str(exc) == trio
    else:
        raise AssertionError("expected the tidyverse error")
