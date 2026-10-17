"""Python translation of checkmate 2.3.4."""

from .asserting import (
    AssertCollection,
    asCount,
    asInt,
    asInteger,
    assertAccess,
    assertArray,
    assertAtomic,
    assertAtomicVector,
    assertCharacter,
    assertChoice,
    assertClass,
    assertComplex,
    assertCount,
    assertDataFrame,
    assertDataTable,
    assertDate,
    assertDirectoryExists,
    assertDisjunct,
    assertDouble,
    assertEnvironment,
    assertFALSE,
    assertFactor,
    assertFileExists,
    assertFlag,
    assertFormula,
    assertFunction,
    assertInt,
    assertInteger,
    assertIntegerish,
    assertList,
    assertLogical,
    assertMatrix,
    assertMultiClass,
    assertNamed,
    assertNames,
    assertNull,
    assertNumber,
    assertNumeric,
    assertOS,
    assertPOSIXct,
    assertPathForOutput,
    assertPermutation,
    assertR6,
    assertRaw,
    assertScalar,
    assertScalarNA,
    assertSetEqual,
    assertString,
    assertSubset,
    assertTRUE,
    assertTibble,
    assertVector,
    assert_,
    assert_and,
    assert_or,
    makeAssertCollection,
    makeAssertion,
    makeAssertionFunction,
    makeTest,
    makeTestFunction,
    matchArg,
    reportAssertions,
    testAccess,
    testArray,
    testAtomic,
    testAtomicVector,
    testCharacter,
    testChoice,
    testClass,
    testComplex,
    testCount,
    testDataFrame,
    testDataTable,
    testDate,
    testDirectoryExists,
    testDisjunct,
    testDouble,
    testEnvironment,
    testFALSE,
    testFactor,
    testFileExists,
    testFlag,
    testFormula,
    testFunction,
    testInt,
    testInteger,
    testIntegerish,
    testList,
    testLogical,
    testMatrix,
    testMultiClass,
    testNamed,
    testNames,
    testNull,
    testNumber,
    testNumeric,
    testOS,
    testPOSIXct,
    testPathForOutput,
    testPermutation,
    testR6,
    testRaw,
    testScalar,
    testScalarNA,
    testSetEqual,
    testString,
    testSubset,
    testTRUE,
    testTibble,
    testVector,
    vname,
)
from .checks import (
    checkArray,
    checkAtomic,
    checkAtomicVector,
    checkCharacter,
    checkComplex,
    checkCount,
    checkDataFrame,
    checkDouble,
    checkFactor,
    checkFlag,
    checkInt,
    checkInteger,
    checkIntegerish,
    checkList,
    checkLogical,
    checkMatrix,
    checkNamed,
    checkNames,
    checkNumber,
    checkNumeric,
    checkPOSIXct,
    checkRaw,
    checkScalar,
    checkString,
    checkVector,
    is_integerish as isIntegerish,
)
from .extra import (
    allMissing,
    anyInfinite,
    anyMissing,
    anyNaN,
    checkAccess,
    checkClass,
    checkDataTable,
    checkDate,
    checkDirectoryExists,
    checkEnvironment,
    checkFALSE,
    checkFileExists,
    checkFormula,
    checkFunction,
    checkMultiClass,
    checkNull,
    checkOS,
    checkPathForOutput,
    checkR6,
    checkScalarNA,
    checkTRUE,
    checkTibble,
    coalesce,
    wf,
    wl,
)
from .expectations import (
    expect_access,
    expect_array,
    expect_atomic,
    expect_atomic_vector,
    expect_character,
    expect_choice,
    expect_class,
    expect_complex,
    expect_count,
    expect_data_frame,
    expect_data_table,
    expect_date,
    expect_directory,
    expect_directory_exists,
    expect_disjunct,
    expect_double,
    expect_environment,
    expect_factor,
    expect_file,
    expect_file_exists,
    expect_flag,
    expect_formula,
    expect_function,
    expect_int,
    expect_integer,
    expect_integerish,
    expect_list,
    expect_logical,
    expect_matrix,
    expect_multi_class,
    expect_names,
    expect_number,
    expect_numeric,
    expect_os,
    expect_path_for_output,
    expect_permutation,
    expect_posixct,
    expect_r6,
    expect_raw,
    expect_scalar,
    expect_scalar_na,
    expect_set_equal,
    expect_string,
    expect_subset,
    expect_tibble,
    makeExpectation,
    makeExpectationFunction,
    register_test_backend,
)
from .qassert import qassert, qassertr, qexpect, qexpectr, qtest, qtestr
from .rtypes import (
    NA,
    CheckError,
    Environment,
    Formula,
    Function,
    R6,
    Vec,
    array,
    as_tibble,
    character,
    complex_,
    data_frame,
    data_table,
    date,
    double,
    environment,
    factor,
    formula,
    integer,
    logical,
    matrix,
    posixct,
    raw,
    rlist,
)
from .sets import (
    checkChoice,
    checkDisjunct,
    checkPermutation,
    checkSetEqual,
    checkSubset,
)

check_flag = checkFlag
assert_flag = assertFlag
test_flag = testFlag
check_count = checkCount
assert_count = assertCount
test_count = testCount
check_int = checkInt
assert_int = assertInt
test_int = testInt
check_integer = checkInteger
assert_integer = assertInteger
test_integer = testInteger
check_integerish = checkIntegerish
assert_integerish = assertIntegerish
test_integerish = testIntegerish
check_double = checkDouble
assert_double = assertDouble
test_double = testDouble
check_numeric = checkNumeric
assert_numeric = assertNumeric
test_numeric = testNumeric
check_logical = checkLogical
assert_logical = assertLogical
test_logical = testLogical
check_complex = checkComplex
assert_complex = assertComplex
test_complex = testComplex
check_character = checkCharacter
assert_character = assertCharacter
test_character = testCharacter
check_string = checkString
assert_string = assertString
test_string = testString
check_factor = checkFactor
assert_factor = assertFactor
test_factor = testFactor
check_number = checkNumber
assert_number = assertNumber
test_number = testNumber
check_scalar = checkScalar
assert_scalar = assertScalar
test_scalar = testScalar
check_scalar_na = checkScalarNA
assert_scalar_na = assertScalarNA
test_scalar_na = testScalarNA
check_atomic = checkAtomic
assert_atomic = assertAtomic
test_atomic = testAtomic
check_atomic_vector = checkAtomicVector
assert_atomic_vector = assertAtomicVector
test_atomic_vector = testAtomicVector
check_vector = checkVector
assert_vector = assertVector
test_vector = testVector
check_list = checkList
assert_list = assertList
test_list = testList
check_matrix = checkMatrix
assert_matrix = assertMatrix
test_matrix = testMatrix
check_array = checkArray
assert_array = assertArray
test_array = testArray
check_data_frame = checkDataFrame
assert_data_frame = assertDataFrame
test_data_frame = testDataFrame
check_data_table = checkDataTable
assert_data_table = assertDataTable
test_data_table = testDataTable
check_r6 = checkR6
assert_r6 = assertR6
test_r6 = testR6
check_tibble = checkTibble
assert_tibble = assertTibble
test_tibble = testTibble
check_raw = checkRaw
assert_raw = assertRaw
test_raw = testRaw
check_named = checkNamed
assert_named = assertNamed
test_named = testNamed
check_names = checkNames
assert_names = assertNames
test_names = testNames
check_posixct = checkPOSIXct
assert_posixct = assertPOSIXct
test_posixct = testPOSIXct
check_choice = checkChoice
assert_choice = assertChoice
test_choice = testChoice
check_subset = checkSubset
assert_subset = assertSubset
test_subset = testSubset
check_disjunct = checkDisjunct
assert_disjunct = assertDisjunct
test_disjunct = testDisjunct
check_set_equal = checkSetEqual
assert_set_equal = assertSetEqual
test_set_equal = testSetEqual
check_permutation = checkPermutation
assert_permutation = assertPermutation
test_permutation = testPermutation
check_access = checkAccess
assert_access = assertAccess
test_access = testAccess
check_file_exists = checkFileExists
assert_file_exists = assertFileExists
test_file_exists = testFileExists
checkFile = checkFileExists
assertFile = assertFileExists
assert_file = assert_file_exists
testFile = testFileExists
check_directory_exists = checkDirectoryExists
assert_directory_exists = assertDirectoryExists
test_directory_exists = testDirectoryExists
checkDirectory = checkDirectoryExists
assertDirectory = assertDirectoryExists
assert_directory = assert_directory_exists
testDirectory = testDirectoryExists
test_directory = test_directory_exists
check_path_for_output = checkPathForOutput
assert_path_for_output = assertPathForOutput
test_path_for_output = testPathForOutput
check_class = checkClass
assert_class = assertClass
test_class = testClass
check_multi_class = checkMultiClass
assert_multi_class = assertMultiClass
test_multi_class = testMultiClass
check_function = checkFunction
assert_function = assertFunction
test_function = testFunction
check_formula = checkFormula
assert_formula = assertFormula
test_formula = testFormula
check_environment = checkEnvironment
assert_environment = assertEnvironment
test_environment = testEnvironment
check_date = checkDate
assert_date = assertDate
test_date = testDate
check_null = checkNull
assert_null = assertNull
test_null = testNull
check_true = checkTRUE
assert_true = assertTRUE
test_true = testTRUE
check_false = checkFALSE
assert_false = assertFALSE
test_false = testFALSE
check_os = checkOS
assert_os = assertOS
test_os = testOS

__all__ = [name for name in globals() if not name.startswith("_")]
