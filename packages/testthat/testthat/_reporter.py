"""Reporters are Python classes. R6 is not translated."""

from __future__ import annotations

import os
from contextlib import contextmanager

from testthat._core import STATE, Expectation


def _letter(kind: str) -> str:
    return {"skip": "S", "success": ".", "error": "E", "failure": "F", "warning": "W"}.get(kind, "?")


class Reporter:
    def __init__(self, file=None):
        self.file = file
        self.results: list[Expectation] = []
        self.context = None
        self.out = []
        self.n_fail = 0
        self.n_success = 0
        self.depth = 0
        self.praise = True

    def start_reporter(self):
        return None

    def start_context(self, context):
        self.context = context

    def start_file(self, filename):
        return None

    def start_test(self, context, test):
        if self.depth == 0:
            self.n_fail = 0
            self.n_success = 0
        self.depth += 1

    def add_result(self, context, test, result: Expectation):
        self.results.append(result)
        if result.kind == "success":
            self.n_success += 1
        elif result.kind in {"failure", "error"}:
            self.n_fail += 1

    def end_test(self, context, test):
        self.depth = max(0, self.depth - 1)

    def end_context(self, context):
        return None

    def end_file(self):
        return None

    def end_reporter(self):
        return None

    def is_full(self):
        return False

    def update(self):
        return None

    def cat_line(self, text=""):
        self.out.append(str(text))

    def get_results(self):
        return list(self.results)

    def summary(self) -> str:
        return f"{self.n_success} success {self.n_fail} fail"


class StopReporter(Reporter):
    def end_test(self, context, test):
        super().end_test(context, test)
        if self.depth > 0:
            return
        if self.praise and self.n_fail == 0 and self.n_success > 0:
            self.cat_line(f"Test passed with {self.n_success} success{'es' if self.n_success != 1 else ''}.")
            print(self.out[-1])
        if self.n_fail > 0:
            from testthat._core import stop
            stop(f"Test failed with {self.n_fail} failure{'s' if self.n_fail != 1 else ''} and {self.n_success} success{'es' if self.n_success != 1 else ''}.")


class MinimalReporter(Reporter):
    def add_result(self, context, test, result):
        super().add_result(context, test, result)
        self.out.append(_letter(result.kind))

    def end_reporter(self):
        self.out.append("\n")

    def summary(self) -> str:
        return "".join(self.out).replace("\n", "")


class SilentReporter(Reporter):
    pass


class ListReporter(Reporter):
    pass


class SummaryReporter(Reporter):
    def end_reporter(self):
        self.cat_line(self.summary())


class ProgressReporter(Reporter):
    def add_result(self, context, test, result):
        super().add_result(context, test, result)
        self.out.append(_letter(result.kind))


class CompactProgressReporter(ProgressReporter):
    pass


class ParallelProgressReporter(ProgressReporter):
    pass


class CheckReporter(Reporter):
    pass


class DebugReporter(Reporter):
    pass


class FailReporter(Reporter):
    def add_result(self, context, test, result):
        super().add_result(context, test, result)
        if result.kind in {"failure", "error"}:
            from testthat._core import stop
            stop(result.message)


class LocationReporter(Reporter):
    pass


class JunitReporter(Reporter):
    def end_reporter(self):
        fails = sum(1 for item in self.results if item.kind in {"failure", "error"})
        self.cat_line(f'<testsuite tests="{len(self.results)}" failures="{fails}">')


class LlmReporter(Reporter):
    def end_reporter(self):
        self.cat_line(self.summary())


class RStudioReporter(ProgressReporter):
    pass


class SlowReporter(Reporter):
    pass


class TapReporter(Reporter):
    def __init__(self, file=None):
        super().__init__(file)
        self.index = 0

    def add_result(self, context, test, result):
        super().add_result(context, test, result)
        self.index += 1
        status = "ok" if result.kind in {"success", "warning"} else "not ok"
        self.out.append(f"{status} {self.index}")


class TeamcityReporter(Reporter):
    def start_test(self, context, test):
        super().start_test(context, test)
        self.out.append(f"##teamcity[testStarted name='{test}']")

    def end_test(self, context, test):
        super().end_test(context, test)
        if self.depth == 0:
            self.out.append(f"##teamcity[testFinished name='{test}']")


class MultiReporter(Reporter):
    def __init__(self, reporters):
        super().__init__()
        self.reporters = list(reporters)

    def add_result(self, context, test, result):
        super().add_result(context, test, result)
        for reporter in self.reporters:
            reporter.add_result(context, test, result)


def _is_llm() -> bool:
    return any(os.environ.get(name) for name in ("AGENT", "CLAUDECODE", "GEMINI_CLI", "CURSOR_AGENT"))


def default_reporter(parallel=False):
    if _is_llm():
        return "Llm"
    if parallel:
        return "ParallelProgress"
    return "Progress"


def default_compact_reporter():
    if _is_llm():
        return "Llm"
    return "CompactProgress"


def check_reporter():
    return "Check"


def set_reporter(reporter):
    old = STATE.reporter
    STATE.reporter = reporter
    return old


def get_reporter():
    return STATE.reporter


@contextmanager
def with_reporter(reporter):
    old = set_reporter(reporter)
    try:
        if hasattr(reporter, "start_reporter"):
            reporter.start_reporter()
        yield reporter
    finally:
        if hasattr(reporter, "end_reporter"):
            reporter.end_reporter()
        set_reporter(old)


def set_max_fails(n):
    os.environ["TESTTHAT_MAX_FAILS"] = str(n)
    return True
