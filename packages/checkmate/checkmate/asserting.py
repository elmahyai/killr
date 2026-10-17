"""Assertions, tests, collections, coercion, and matchArg."""

from __future__ import annotations

import math

from . import checks as C
from . import extra as E
from . import sets as S
from .qassert import qassert, qassertr, qtest, qtestr
from .rtypes import (
    DEFAULT_TOL,
    NA,
    CheckError,
    Vec,
    caller_arg,
    is_null,
    message,
    wrap,
    xlength,
)


class AssertCollection:
    r_class = ("AssertCollection",)

    def __init__(self) -> None:
        self._messages: list[str] = []

    def push(self, msg: str) -> None:
        self._messages.append(msg)

    def getMessages(self) -> list[str]:
        return list(self._messages)

    def isEmpty(self) -> bool:
        return not self._messages

    def __str__(self) -> str:
        n = len(self._messages)
        if n == 0:
            return "Empty collection"
        suffix = "s" if n > 1 else ""
        return f"Collection of {n} assertion{suffix}."


def makeAssertCollection() -> AssertCollection:
    return AssertCollection()


def reportAssertions(collection):
    assertClass(collection, "AssertCollection", var_name="collection")
    if not collection.isEmpty():
        msgs = collection.getMessages()
        err = [f"{len(msgs)} assertions failed:", *[f" * {item}" for item in msgs]]
        raise CheckError("\n".join(err))
    return True


def makeAssertion(x, res, var_name, collection=None):
    if res is not True:
        name_hit = C.checkString(var_name)
        if name_hit is not True:
            raise CheckError(f"Assertion on '.var.name' failed: {name_hit}.")
        if collection is None:
            raise CheckError(f"Assertion on '{var_name}' failed: {res}.")
        if not isinstance(collection, AssertCollection):
            raise CheckError("Assertion on 'add' failed: Must be of class 'AssertCollection'.")
        collection.push(f"Variable '{var_name}': {res}.")
    return x


def makeTest(res) -> bool:
    return res is True


def _call(check, args, kwargs):
    return check(*args, **kwargs)


def _assert(check, args, kwargs, var_name, add, coerce_value=None):
    if var_name is None:
        var_name = caller_arg(3)
    res = _call(check, args, kwargs)
    out = makeAssertion(args[0] if args else kwargs.get("x"), res, var_name, add)
    if coerce_value and res is True:
        return _coerce_integer(out)
    return out


def _coerce_integer(value):
    obj = wrap(value)
    if not (isinstance(obj, Vec) and obj.mode == "double"):
        return value
    data = []
    for item in obj.data:
        if item is NA or (isinstance(item, float) and math.isnan(item)):
            data.append(NA)
        else:
            data.append(int(round(float(item))))
    return Vec("integer", data, names=obj.names, dim=obj.dim, klass=obj.klass)


def _test(check, args, kwargs) -> bool:
    return makeTest(_call(check, args, kwargs))


def assertFlag(x, na_ok=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkFlag, (x,), {"na_ok": na_ok, "null_ok": null_ok}, var_name, add)


def assertCount(x, na_ok=False, positive=False, tol=DEFAULT_TOL, null_ok=False, var_name=None, add=None, coerce=False):
    return _assert(C.checkCount, (x,), {"na_ok": na_ok, "positive": positive, "tol": tol, "null_ok": null_ok}, var_name, add, coerce)


def assertInt(x, na_ok=False, lower=-math.inf, upper=math.inf, tol=DEFAULT_TOL, null_ok=False, var_name=None, add=None, coerce=False):
    return _assert(C.checkInt, (x,), {"na_ok": na_ok, "lower": lower, "upper": upper, "tol": tol, "null_ok": null_ok}, var_name, add, coerce)


def assertInteger(x, lower=-math.inf, upper=math.inf, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkInteger, (x,), dict(lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok), var_name, add)


def assertIntegerish(x, tol=DEFAULT_TOL, lower=-math.inf, upper=math.inf, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False, var_name=None, add=None, coerce=False):
    return _assert(C.checkIntegerish, (x,), dict(tol=tol, lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok), var_name, add, coerce)


def assertDouble(x, lower=-math.inf, upper=math.inf, finite=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkDouble, (x,), dict(lower=lower, upper=upper, finite=finite, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok), var_name, add)


def assertNumeric(x, lower=-math.inf, upper=math.inf, finite=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkNumeric, (x,), dict(lower=lower, upper=upper, finite=finite, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok), var_name, add)


def assertLogical(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, typed_missing=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkLogical, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, typed_missing=typed_missing, null_ok=null_ok), var_name, add)


def assertComplex(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, typed_missing=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkComplex, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, typed_missing=typed_missing, null_ok=null_ok), var_name, add)


def assertCharacter(x, n_chars=None, min_chars=None, max_chars=None, pattern=None, fixed=None, ignore_case=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkCharacter, (x,), dict(n_chars=n_chars, min_chars=min_chars, max_chars=max_chars, pattern=pattern, fixed=fixed, ignore_case=ignore_case, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok), var_name, add)


def assertString(x, na_ok=False, n_chars=None, min_chars=None, max_chars=None, pattern=None, fixed=None, ignore_case=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkString, (x,), dict(na_ok=na_ok, n_chars=n_chars, min_chars=min_chars, max_chars=max_chars, pattern=pattern, fixed=fixed, ignore_case=ignore_case, null_ok=null_ok), var_name, add)


def assertFactor(x, levels=None, ordered=NA, empty_levels_ok=True, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, n_levels=None, min_levels=None, max_levels=None, unique=False, names=None, null_ok=False, var_name=None, add=None):
    return _assert(C.checkFactor, (x,), dict(levels=levels, ordered=ordered, empty_levels_ok=empty_levels_ok, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, n_levels=n_levels, min_levels=min_levels, max_levels=max_levels, unique=unique, names=names, null_ok=null_ok), var_name, add)


def assertNumber(x, na_ok=False, lower=-math.inf, upper=math.inf, finite=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkNumber, (x,), dict(na_ok=na_ok, lower=lower, upper=upper, finite=finite, null_ok=null_ok), var_name, add)


def assertScalar(x, na_ok=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkScalar, (x,), dict(na_ok=na_ok, null_ok=null_ok), var_name, add)


def assertAtomic(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, var_name=None, add=None):
    return _assert(C.checkAtomic, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names), var_name, add)


def assertAtomicVector(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, var_name=None, add=None):
    return _assert(C.checkAtomicVector, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names), var_name, add)


def assertVector(x, strict=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, null_ok=False, var_name=None, add=None):
    return _assert(C.checkVector, (x,), dict(strict=strict, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, null_ok=null_ok), var_name, add)


def assertList(x, types=None, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, null_ok=False, var_name=None, add=None):
    return _assert(C.checkList, (x,), dict(types=types, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, null_ok=null_ok), var_name, add)


def assertMatrix(x, mode=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False, var_name=None, add=None):
    return _assert(C.checkMatrix, (x,), dict(mode=mode, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok), var_name, add)


def assertArray(x, mode=None, any_missing=True, d=None, min_d=None, max_d=None, null_ok=False, var_name=None, add=None):
    return _assert(C.checkArray, (x,), dict(mode=mode, any_missing=any_missing, d=d, min_d=min_d, max_d=max_d, null_ok=null_ok), var_name, add)


def assertDataFrame(x, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False, var_name=None, add=None):
    return _assert(C.checkDataFrame, (x,), dict(types=types, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok), var_name, add)


def assertDataTable(x, key=None, index=None, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False, var_name=None, add=None):
    return _assert(E.checkDataTable, (x,), dict(key=key, index=index, types=types, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok), var_name, add)


def assertR6(x, classes=None, ordered=False, cloneable=None, public=None, private=None, null_ok=False, var_name=None, add=None):
    return _assert(E.checkR6, (x,), dict(classes=classes, ordered=ordered, cloneable=cloneable, public=public, private=private, null_ok=null_ok), var_name, add)


def assertTibble(x, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False, var_name=None, add=None):
    return _assert(E.checkTibble, (x,), dict(types=types, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok), var_name, add)


def assertRaw(x, len=None, min_len=None, max_len=None, names=None, null_ok=False, var_name=None, add=None):
    return _assert(C.checkRaw, (x,), dict(len=len, min_len=min_len, max_len=max_len, names=names, null_ok=null_ok), var_name, add)


def assertNamed(x, type="named", var_name=None, add=None):
    return _assert(C.checkNamed, (x,), {"type": type}, var_name, add)


def assertNames(x, type="named", subset_of=None, must_include=None, permutation_of=None, identical_to=None, disjunct_from=None, what="names", var_name=None, add=None):
    return _assert(C.checkNames, (x,), dict(type=type, subset_of=subset_of, must_include=must_include, permutation_of=permutation_of, identical_to=identical_to, disjunct_from=disjunct_from, what=what), var_name, add)


def assertPOSIXct(x, lower=None, upper=None, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, null_ok=False, var_name=None, add=None):
    return _assert(C.checkPOSIXct, (x,), dict(lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, null_ok=null_ok), var_name, add)


def assertChoice(x, choices, null_ok=False, fmatch=False, var_name=None, add=None):
    return _assert(S.checkChoice, (x, choices), {"null_ok": null_ok, "fmatch": fmatch}, var_name, add)


def assertSubset(x, choices, empty_ok=True, fmatch=False, var_name=None, add=None):
    return _assert(S.checkSubset, (x, choices), {"empty_ok": empty_ok, "fmatch": fmatch}, var_name, add)


def assertDisjunct(x, y, fmatch=False, var_name=None, add=None):
    return _assert(S.checkDisjunct, (x, y), {"fmatch": fmatch}, var_name, add)


def assertSetEqual(x, y, ordered=False, fmatch=False, var_name=None, add=None):
    return _assert(S.checkSetEqual, (x, y), {"ordered": ordered, "fmatch": fmatch}, var_name, add)


def assertPermutation(x, y, na_ok=True, var_name=None, add=None):
    return _assert(S.checkPermutation, (x, y), {"na_ok": na_ok}, var_name, add)


def assertAccess(x, access="", var_name=None, add=None):
    return _assert(E.checkAccess, (x,), {"access": access}, var_name, add)


def assertFileExists(x, access="", extension=None, var_name=None, add=None):
    return _assert(E.checkFileExists, (x,), {"access": access, "extension": extension}, var_name, add)


def assertDirectoryExists(x, access="", var_name=None, add=None):
    return _assert(E.checkDirectoryExists, (x,), {"access": access}, var_name, add)


def assertPathForOutput(x, overwrite=False, extension=None, var_name=None, add=None):
    return _assert(E.checkPathForOutput, (x,), {"overwrite": overwrite, "extension": extension}, var_name, add)


def assertClass(x, classes, ordered=False, null_ok=False, var_name=None, add=None):
    return _assert(E.checkClass, (x, classes), {"ordered": ordered, "null_ok": null_ok}, var_name, add)


def assertMultiClass(x, classes, null_ok=False, var_name=None, add=None):
    return _assert(E.checkMultiClass, (x, classes), {"null_ok": null_ok}, var_name, add)


def assertFunction(x, args=None, ordered=False, nargs=None, null_ok=False, var_name=None, add=None):
    return _assert(E.checkFunction, (x,), {"args": args, "ordered": ordered, "nargs": nargs, "null_ok": null_ok}, var_name, add)


def assertFormula(x, null_ok=False, var_name=None, add=None):
    return _assert(E.checkFormula, (x,), {"null_ok": null_ok}, var_name, add)


def assertEnvironment(x, contains=None, null_ok=False, var_name=None, add=None):
    return _assert(E.checkEnvironment, (x,), {"contains": contains, "null_ok": null_ok}, var_name, add)


def assertDate(x, lower=None, upper=None, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, null_ok=False, var_name=None, add=None):
    return _assert(E.checkDate, (x,), dict(lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, null_ok=null_ok), var_name, add)


def assertNull(x, var_name=None, add=None):
    return _assert(E.checkNull, (x,), {}, var_name, add)


def assertTRUE(x, na_ok=False, var_name=None, add=None):
    return _assert(E.checkTRUE, (x,), {"na_ok": na_ok}, var_name, add)


def assertFALSE(x, na_ok=False, var_name=None, add=None):
    return _assert(E.checkFALSE, (x,), {"na_ok": na_ok}, var_name, add)


def assertScalarNA(x, null_ok=False, var_name=None, add=None):
    return _assert(E.checkScalarNA, (x,), {"null_ok": null_ok}, var_name, add)


def assertOS(os, add=None, var_name=None):
    res = E.checkOS(os)
    return makeAssertion(os, res, var_name if var_name is not None else "Operating System", add)


def testFlag(x, na_ok=False, null_ok=False):
    return _test(C.checkFlag, (x,), {"na_ok": na_ok, "null_ok": null_ok})


def testCount(x, na_ok=False, positive=False, tol=DEFAULT_TOL, null_ok=False):
    return _test(C.checkCount, (x,), {"na_ok": na_ok, "positive": positive, "tol": tol, "null_ok": null_ok})


def testInt(x, na_ok=False, lower=-math.inf, upper=math.inf, tol=DEFAULT_TOL, null_ok=False):
    return _test(C.checkInt, (x,), {"na_ok": na_ok, "lower": lower, "upper": upper, "tol": tol, "null_ok": null_ok})


def testInteger(x, lower=-math.inf, upper=math.inf, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False):
    return _test(C.checkInteger, (x,), dict(lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok))


def testIntegerish(x, tol=DEFAULT_TOL, lower=-math.inf, upper=math.inf, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False):
    return _test(C.checkIntegerish, (x,), dict(tol=tol, lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok))


def testDouble(x, lower=-math.inf, upper=math.inf, finite=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False):
    return _test(C.checkDouble, (x,), dict(lower=lower, upper=upper, finite=finite, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok))


def testNumeric(x, lower=-math.inf, upper=math.inf, finite=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False):
    return _test(C.checkNumeric, (x,), dict(lower=lower, upper=upper, finite=finite, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok))


def testLogical(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, typed_missing=False, null_ok=False):
    return _test(C.checkLogical, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, typed_missing=typed_missing, null_ok=null_ok))


def testComplex(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, typed_missing=False, null_ok=False):
    return _test(C.checkComplex, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, typed_missing=typed_missing, null_ok=null_ok))


def testCharacter(x, n_chars=None, min_chars=None, max_chars=None, pattern=None, fixed=None, ignore_case=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, typed_missing=False, null_ok=False):
    return _test(C.checkCharacter, (x,), dict(n_chars=n_chars, min_chars=min_chars, max_chars=max_chars, pattern=pattern, fixed=fixed, ignore_case=ignore_case, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, typed_missing=typed_missing, null_ok=null_ok))


def testString(x, na_ok=False, n_chars=None, min_chars=None, max_chars=None, pattern=None, fixed=None, ignore_case=False, null_ok=False):
    return _test(C.checkString, (x,), dict(na_ok=na_ok, n_chars=n_chars, min_chars=min_chars, max_chars=max_chars, pattern=pattern, fixed=fixed, ignore_case=ignore_case, null_ok=null_ok))


def testFactor(x, levels=None, ordered=NA, empty_levels_ok=True, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, n_levels=None, min_levels=None, max_levels=None, unique=False, names=None, null_ok=False):
    return _test(C.checkFactor, (x,), dict(levels=levels, ordered=ordered, empty_levels_ok=empty_levels_ok, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, n_levels=n_levels, min_levels=min_levels, max_levels=max_levels, unique=unique, names=names, null_ok=null_ok))


def testNumber(x, na_ok=False, lower=-math.inf, upper=math.inf, finite=False, null_ok=False):
    return _test(C.checkNumber, (x,), dict(na_ok=na_ok, lower=lower, upper=upper, finite=finite, null_ok=null_ok))


def testScalar(x, na_ok=False, null_ok=False):
    return _test(C.checkScalar, (x,), dict(na_ok=na_ok, null_ok=null_ok))


def testAtomic(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None):
    return _test(C.checkAtomic, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names))


def testAtomicVector(x, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None):
    return _test(C.checkAtomicVector, (x,), dict(any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names))


def testVector(x, strict=False, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, null_ok=False):
    return _test(C.checkVector, (x,), dict(strict=strict, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, null_ok=null_ok))


def testList(x, types=None, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, names=None, null_ok=False):
    return _test(C.checkList, (x,), dict(types=types, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, names=names, null_ok=null_ok))


def testMatrix(x, mode=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False):
    return _test(C.checkMatrix, (x,), dict(mode=mode, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok))


def testArray(x, mode=None, any_missing=True, d=None, min_d=None, max_d=None, null_ok=False):
    return _test(C.checkArray, (x,), dict(mode=mode, any_missing=any_missing, d=d, min_d=min_d, max_d=max_d, null_ok=null_ok))


def testDataFrame(x, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False):
    return _test(C.checkDataFrame, (x,), dict(types=types, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok))


def testDataTable(x, key=None, index=None, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False):
    return _test(E.checkDataTable, (x,), dict(key=key, index=index, types=types, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok))


def testR6(x, classes=None, ordered=False, cloneable=None, public=None, private=None, null_ok=False):
    return _test(E.checkR6, (x,), dict(classes=classes, ordered=ordered, cloneable=cloneable, public=public, private=private, null_ok=null_ok))


def testTibble(x, types=None, any_missing=True, all_missing=True, min_rows=None, max_rows=None, min_cols=None, max_cols=None, nrows=None, ncols=None, row_names=None, col_names=None, null_ok=False):
    return _test(E.checkTibble, (x,), dict(types=types, any_missing=any_missing, all_missing=all_missing, min_rows=min_rows, max_rows=max_rows, min_cols=min_cols, max_cols=max_cols, nrows=nrows, ncols=ncols, row_names=row_names, col_names=col_names, null_ok=null_ok))


def testRaw(x, len=None, min_len=None, max_len=None, names=None, null_ok=False):
    return _test(C.checkRaw, (x,), dict(len=len, min_len=min_len, max_len=max_len, names=names, null_ok=null_ok))


def testNamed(x, type="named"):
    return _test(C.checkNamed, (x,), {"type": type})


def testNames(x, type="named", subset_of=None, must_include=None, permutation_of=None, identical_to=None, disjunct_from=None, what="names"):
    return _test(C.checkNames, (x,), dict(type=type, subset_of=subset_of, must_include=must_include, permutation_of=permutation_of, identical_to=identical_to, disjunct_from=disjunct_from, what=what))


def testPOSIXct(x, lower=None, upper=None, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, null_ok=False):
    return _test(C.checkPOSIXct, (x,), dict(lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, null_ok=null_ok))


def testChoice(x, choices, null_ok=False, fmatch=False):
    return _test(S.checkChoice, (x, choices), {"null_ok": null_ok, "fmatch": fmatch})


def testSubset(x, choices, empty_ok=True, fmatch=False):
    return _test(S.checkSubset, (x, choices), {"empty_ok": empty_ok, "fmatch": fmatch})


def testDisjunct(x, y, fmatch=False):
    return _test(S.checkDisjunct, (x, y), {"fmatch": fmatch})


def testSetEqual(x, y, ordered=False, fmatch=False):
    return _test(S.checkSetEqual, (x, y), {"ordered": ordered, "fmatch": fmatch})


def testPermutation(x, y, na_ok=True):
    return _test(S.checkPermutation, (x, y), {"na_ok": na_ok})


def testAccess(x, access=""):
    return _test(E.checkAccess, (x,), {"access": access})


def testFileExists(x, access="", extension=None):
    return _test(E.checkFileExists, (x,), {"access": access, "extension": extension})


def testDirectoryExists(x, access=""):
    return _test(E.checkDirectoryExists, (x,), {"access": access})


def testPathForOutput(x, overwrite=False, extension=None):
    return _test(E.checkPathForOutput, (x,), {"overwrite": overwrite, "extension": extension})


def testClass(x, classes, ordered=False, null_ok=False):
    return _test(E.checkClass, (x, classes), {"ordered": ordered, "null_ok": null_ok})


def testMultiClass(x, classes, null_ok=False):
    return _test(E.checkMultiClass, (x, classes), {"null_ok": null_ok})


def testFunction(x, args=None, ordered=False, nargs=None, null_ok=False):
    return _test(E.checkFunction, (x,), {"args": args, "ordered": ordered, "nargs": nargs, "null_ok": null_ok})


def testFormula(x, null_ok=False):
    return _test(E.checkFormula, (x,), {"null_ok": null_ok})


def testEnvironment(x, contains=None, null_ok=False):
    return _test(E.checkEnvironment, (x,), {"contains": contains, "null_ok": null_ok})


def testDate(x, lower=None, upper=None, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, null_ok=False):
    return _test(E.checkDate, (x,), dict(lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, null_ok=null_ok))


def testNull(x):
    return _test(E.checkNull, (x,), {})


def testTRUE(x, na_ok=False):
    return _test(E.checkTRUE, (x,), {"na_ok": na_ok})


def testFALSE(x, na_ok=False):
    return _test(E.checkFALSE, (x,), {"na_ok": na_ok})


def testScalarNA(x, null_ok=False):
    return _test(E.checkScalarNA, (x,), {"null_ok": null_ok})


def testOS(os):
    return _test(E.checkOS, (os,), {})


def asInteger(x, tol=DEFAULT_TOL, lower=-math.inf, upper=math.inf, any_missing=True, all_missing=True, len=None, min_len=None, max_len=None, unique=False, sorted=False, names=None, var_name=None):
    assertIntegerish(x, tol=tol, lower=lower, upper=upper, any_missing=any_missing, all_missing=all_missing, len=len, min_len=min_len, max_len=max_len, unique=unique, sorted=sorted, names=names, null_ok=False, var_name=var_name)
    obj = wrap(x)
    data = []
    for item in obj.data:
        if item is NA or (isinstance(item, float) and math.isnan(item)):
            data.append(NA)
        else:
            data.append(int(float(item)))
    return Vec("integer", data, names=obj.names)


def asCount(x, na_ok=False, positive=False, tol=DEFAULT_TOL, var_name=None):
    assertCount(x, na_ok, positive, tol, var_name=var_name)
    obj = wrap(x)
    item = obj.data[0]
    value = NA if item is NA or (isinstance(item, float) and math.isnan(item)) else int(float(item))
    return Vec("integer", [value], names=obj.names)


def asInt(x, na_ok=False, lower=-math.inf, upper=math.inf, tol=DEFAULT_TOL, var_name=None):
    assertInt(x, na_ok, lower, upper, tol, var_name=var_name)
    obj = wrap(x)
    item = obj.data[0]
    value = NA if item is NA or (isinstance(item, float) and math.isnan(item)) else int(float(item))
    return Vec("integer", [value], names=obj.names)


def _pmatch_one(name: str, choices: list[str], taken: set[int] | None) -> int | None:
    exact = [i for i, choice in enumerate(choices) if choice == name and (taken is None or i not in taken)]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    partial = [i for i, choice in enumerate(choices) if choice.startswith(name) and (taken is None or i not in taken)]
    if len(partial) == 1:
        return partial[0]
    return None


def matchArg(x, choices, several_ok=False, var_name=None, add=None):
    assertCharacter(choices, min_len=1, var_name="choices")
    assertFlag(several_ok, var_name="several.ok")
    pool = list(wrap(choices).data)
    given = wrap(x)
    if several_ok:
        if isinstance(x, Vec) and list(x.data) == pool or (isinstance(given, Vec) and given.data == pool and given.mode == "character"):
            return Vec("character", pool)
        assertCharacter(x, min_len=1, var_name=var_name, add=add)
        indexes = []
        for name in wrap(x).data:
            hit = _pmatch_one(name, pool, None)
            indexes.append(hit)
        matched = [pool[i] for i in indexes if i is not None]
        assertSubset(Vec("character", matched), pool, empty_ok=False, var_name=var_name, add=add)
        return Vec("character", matched)
    if isinstance(given, Vec) and given.data == pool:
        return Vec("character", [pool[0]])
    assertCharacter(x, len=1, var_name=var_name, add=add)
    hit = _pmatch_one(wrap(x).data[0], pool, None)
    matched = [] if hit is None else [pool[hit]]
    assertChoice(Vec("character", matched) if matched else Vec("character", []), pool, var_name=var_name, add=add)
    return Vec("character", matched)


def vname(x=None) -> str:
    return caller_arg(2)


def assert_(*results, combine="or", var_name=None, add=None, names=None):
    if combine == "and":
        return assert_and(*results, names=names, var_name=var_name, add=add)
    return assert_or(*results, names=names, var_name=var_name, add=add)


def assert_or(*results, names=None, var_name=None, add=None):
    """combine = 'or'. results are check return values."""
    assertChoice(combine_literal("or"), ["or", "and"])
    if add is not None:
        assertClass(add, "AssertCollection", var_name="add", null_ok=True)
    for item in results:
        if item is True:
            return True
    msgs = [str(item) for item in results]
    labels = list(names) if names is not None else ["x"] * len(results)
    if len(msgs) > 1:
        lines = [f"{label}: {msg}" for label, msg in zip(["check"] * len(msgs), msgs)]
        text = "One of the following must apply:\n" + "\n".join(f" * {line}" for line in lines)
        _stop_or_push(text, labels if var_name is None else var_name, add)
    else:
        _stop_or_push(msgs[0], labels[0] if var_name is None else var_name, add)
    return True


def assert_and(*results, names=None, var_name=None, add=None):
    labels = list(names) if names is not None else ["x"] * len(results)
    for item, label in zip(results, labels):
        if item is not True:
            _stop_or_push(str(item), var_name if var_name is not None else label, add)
    return True


def combine_literal(text):
    return text


def _stop_or_push(res, v_name, collection):
    if collection is not None:
        names = sorted(set(v_name if isinstance(v_name, list) else [v_name]))
        if len(names) > 1:
            prefix = "Variables " + ", ".join(f"'{name}'" for name in names)
        else:
            prefix = f"Variable '{names[0]}'"
        collection.push(f"{prefix}: {res}.")
        return
    if isinstance(v_name, list) and len(v_name) > 1:
        raise CheckError(f"Assertion failed. {res}")
    shown = v_name[0] if isinstance(v_name, list) else v_name
    raise CheckError(f"Assertion on '{shown}' failed: {res}.")


def makeAssertionFunction(check, use_namespace=True, coerce=False, env=None):
    def built(*args, var_name=None, add=None, **kwargs):
        return _assert(check, args, kwargs, var_name, add, kwargs.pop("coerce", False) if coerce else False)
    return built


def makeTestFunction(check, env=None):
    def built(*args, **kwargs):
        return _test(check, args, kwargs)
    return built
