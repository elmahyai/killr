"""testthat and tinytest expectation wrappers for checkmate."""

from __future__ import annotations

import inspect

from . import checks as C
from . import extra as E
from . import sets as S
from .rtypes import CheckError, caller_arg

_backend = {"name": None}


class Tinytest:
    """The object tinytest::tinytest returns."""

    def __init__(self, result: bool, call: str, diff=None, short=None, info=None):
        self.result = result
        self.call = call
        self.diff = diff
        self.short = short
        self.info = info

    def __str__(self) -> str:
        if self.result:
            return f"----- PASSED      : <-->\n call| {self.call} "
        lines = [f"----- FAILED[data]: <-->\n call| {self.call}"]
        if self.diff:
            lines.append(f" diff| {self.diff}")
        if self.info is not None:
            lines.append(f" info| {self.info}")
        return "\n".join(lines)


def get_test_backend() -> str:
    if _backend["name"] is None:
        _backend["name"] = "testthat"
    return _backend["name"]


def register_test_backend(name):
    if isinstance(name, str) and name not in {"testthat", "tinytest"}:
        raise CheckError("'arg' should be one of “testthat”, “tinytest”")
    from .asserting import matchArg

    chosen = matchArg(name, ["testthat", "tinytest"])
    _backend["name"] = chosen.data[0]
    return None


def makeExpectation(x, res, info=None, label=None):
    backend = get_test_backend()
    if backend == "tinytest":
        call = label if label is not None else "expect"
        if res is True:
            return Tinytest(True, call)
        return Tinytest(False, call, diff=res if isinstance(res, str) else "", short="data", info=info)
    if info is not None:
        info = f"Additional info: {info}"
    if res is not True:
        text = f"Check on '{label}' failed: {res}"
        if info is not None:
            text = text + "\n" + info
        raise CheckError(text)
    return x


def makeExpectationFunction(check, c_fun=None, use_namespace=False, env=None):
    signature = inspect.signature(check)
    parameters = list(signature.parameters.values())
    parameters.append(inspect.Parameter("info", inspect.Parameter.KEYWORD_ONLY, default=None))
    parameters.append(inspect.Parameter("label", inspect.Parameter.KEYWORD_ONLY, default=None))

    def built(*args, **kwargs):
        bound = built.__signature__.bind(*args, **kwargs)
        bound.apply_defaults()
        info = bound.arguments.pop("info")
        label = bound.arguments.pop("label")
        if label is None:
            label = caller_arg(2)
        if not bound.arguments:
            raise CheckError(f"Argument '{label}' is missing")
        result = check(**bound.arguments)
        value = bound.arguments.get("x", args[0] if args else None)
        return makeExpectation(value, result, info, label)

    built.__signature__ = signature.replace(parameters=parameters)
    return built


expect_flag = makeExpectationFunction(C.checkFlag)
expect_count = makeExpectationFunction(C.checkCount)
expect_int = makeExpectationFunction(C.checkInt)
expect_integer = makeExpectationFunction(C.checkInteger)
expect_integerish = makeExpectationFunction(C.checkIntegerish)
expect_double = makeExpectationFunction(C.checkDouble)
expect_numeric = makeExpectationFunction(C.checkNumeric)
expect_logical = makeExpectationFunction(C.checkLogical)
expect_complex = makeExpectationFunction(C.checkComplex)
expect_character = makeExpectationFunction(C.checkCharacter)
expect_string = makeExpectationFunction(C.checkString)
expect_factor = makeExpectationFunction(C.checkFactor)
expect_number = makeExpectationFunction(C.checkNumber)
expect_scalar = makeExpectationFunction(C.checkScalar)
expect_scalar_na = makeExpectationFunction(E.checkScalarNA)
expect_atomic = makeExpectationFunction(C.checkAtomic)
expect_atomic_vector = makeExpectationFunction(C.checkAtomicVector)
expect_list = makeExpectationFunction(C.checkList)
expect_matrix = makeExpectationFunction(C.checkMatrix)
expect_array = makeExpectationFunction(C.checkArray)
expect_data_frame = makeExpectationFunction(C.checkDataFrame)
expect_data_table = makeExpectationFunction(E.checkDataTable)
expect_raw = makeExpectationFunction(C.checkRaw)
expect_names = makeExpectationFunction(C.checkNames)
expect_posixct = makeExpectationFunction(C.checkPOSIXct)
expect_choice = makeExpectationFunction(S.checkChoice)
expect_subset = makeExpectationFunction(S.checkSubset)
expect_disjunct = makeExpectationFunction(S.checkDisjunct)
expect_set_equal = makeExpectationFunction(S.checkSetEqual)
expect_permutation = makeExpectationFunction(S.checkPermutation)
expect_access = makeExpectationFunction(E.checkAccess)
expect_file = makeExpectationFunction(E.checkFileExists)
expect_file_exists = makeExpectationFunction(E.checkFileExists)
expect_directory = makeExpectationFunction(E.checkDirectoryExists)
expect_directory_exists = makeExpectationFunction(E.checkDirectoryExists)
expect_path_for_output = makeExpectationFunction(E.checkPathForOutput)
expect_class = makeExpectationFunction(E.checkClass)
expect_multi_class = makeExpectationFunction(E.checkMultiClass)
expect_function = makeExpectationFunction(E.checkFunction)
expect_formula = makeExpectationFunction(E.checkFormula)
expect_environment = makeExpectationFunction(E.checkEnvironment)
expect_date = makeExpectationFunction(E.checkDate)
expect_os = makeExpectationFunction(E.checkOS)
expect_r6 = makeExpectationFunction(E.checkR6)
expect_tibble = makeExpectationFunction(E.checkTibble)
