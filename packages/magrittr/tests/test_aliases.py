"""Checks for the magrittr operator aliases."""

import math
import warnings

import pytest

from magrittr.aliases import (
    NA,
    Matrix,
    RList,
    Vector,
    add,
    and_,
    divide_by,
    divide_by_int,
    equals,
    extract,
    extract2,
    inset,
    inset2,
    is_greater_than,
    is_in,
    is_less_than,
    is_weakly_greater_than,
    is_weakly_less_than,
    mod,
    multiply_by,
    multiply_by_matrix,
    nest_pas,
    not_,
    or_,
    raise_to_power,
    set_attr,
    set_attributes,
    set_class,
    set_colnames,
    set_names,
    set_rownames,
    subtract,
    use_series,
)


def test_add_keeps_names_from_the_longer_vector():
    result = add(Vector([1, 2, 3, 4], ["a", "b", "c", "d"]), [10, 20])
    assert result.pairs() == [("a", 11), ("b", 22), ("c", 13), ("d", 24)]
    assert add(2, 3) == 5


def test_equal_lengths_take_the_left_names_then_the_right():
    assert add(Vector([1, 2], ["a", "b"]), Vector([10, 20], ["x", "y"])).names == ["a", "b"]
    assert add([1, 2], Vector([10, 20], ["x", "y"])).names == ["x", "y"]
    assert add(Vector([1, 2], ["a", "b"]), [10, 20, 30, 40]) == [11, 22, 31, 42]


def test_recycling_warns_when_the_lengths_are_not_multiples():
    with pytest.warns(UserWarning, match="not a multiple"):
        assert add([1, 2, 3], [10, 20]) == [11, 22, 13]


def test_subtract_multiply_divide_and_power():
    assert subtract(Vector([5, 1], ["a", "b"]), [2, 3]).pairs() == [("a", 3), ("b", -2)]
    assert subtract([1, -2]) == [-1, 2]
    assert multiply_by([2, 3, 4, 5], [10, 0.5]) == [20, 1.5, 40, 2.5]
    assert divide_by([1, 2, 3], 2) == [0.5, 1.0, 1.5]
    assert raise_to_power([2, 3, 4], [3, 2, 0.5]) == [8, 9, 2.0]


def test_floor_division_and_modulo_follow_r():
    assert divide_by_int(-7, 2) == -4
    assert divide_by_int([-7, 7, -8, 8], [2, -3]) == [-4, -3, -4, -3]
    assert mod(-7, 2) == 1
    assert mod([-7, 7, 8, -8], [2, -3]) == [1, -2, 0, -2]
    assert math.isnan(divide_by_int(0, 0))
    assert divide_by_int(1, 0) == math.inf
    assert divide_by_int(-1, 0) == -math.inf
    assert math.isnan(mod(1, 0))


def test_matrix_product_is_filled_down_columns():
    left = Matrix([1, 2, 3, 4, 5, 6], nrow=2)
    right = Matrix([1, 2, 3, 4, 5, 6], nrow=3)
    assert left.cells() == [[1, 3, 5], [2, 4, 6]]
    assert right.cells() == [[1, 4], [2, 5], [3, 6]]
    assert multiply_by_matrix(left, right).cells() == [[22.0, 49.0], [28.0, 64.0]]
    assert multiply_by_matrix([1, 2, 3], [4, 5, 6]).cells() == [[32.0]]
    assert multiply_by_matrix([1, 2], left).cells() == [[5.0, 11.0, 17.0]]
    assert multiply_by_matrix(left, [1, 2, 3]).cells() == [[22.0], [28.0]]
    with pytest.raises(ValueError, match="non-conformable"):
        multiply_by_matrix([1, 2], [1, 2, 3])


def test_is_in_is_vectorized_on_the_left():
    assert is_in([1, 3, 5, 3], [3, 5, 7]) == [False, True, True, True]
    assert is_in(["a", "b", "c"], ["b", "c"]) == [False, True, True]
    assert is_in([NA, 1], [NA, 2]) == [True, False]


def test_logical_operators_are_elementwise():
    assert and_([True, True, False, False], [True, False, True, False]) == [
        True,
        False,
        False,
        False,
    ]
    assert or_([True, True, False, False], [True, False, True, False]) == [
        True,
        True,
        True,
        False,
    ]
    assert and_(False, NA) is False
    assert and_(True, NA) is None
    assert or_(True, NA) is True
    assert or_(False, NA) is None
    assert not_([True, False]) == [False, True]
    assert not_([0, 2, 1]) == [True, False, False]
    assert nest_pas is not_
    assert nest_pas([True, False, True]) == [False, True, False]


def test_comparisons():
    assert equals([1, 2, 3], [1, 0, 3]) == [True, False, True]
    assert equals(NA, NA) is None
    assert is_greater_than([1, 2, 3], 2) == [False, False, True]
    assert is_weakly_greater_than([1, 2, 3], 2) == [False, True, True]
    assert is_less_than([1, 2, 3], 2) == [True, False, False]
    assert is_weakly_less_than([1, 2, 3], 2) == [True, True, False]


def test_extract_is_one_based_and_keeps_names():
    values = Vector([10, 20, 30, 40], ["a", "b", "c", "d"])
    assert extract(values, [2, 4]).pairs() == [("b", 20), ("d", 40)]
    assert extract(values, -2).pairs() == [("a", 10), ("c", 30), ("d", 40)]
    assert extract(values, [0, 2, 0]).pairs() == [("b", 20)]
    assert extract(values, [True, False]).pairs() == [("a", 10), ("c", 30)]
    assert extract(values, ["c", "a"]).pairs() == [("c", 30), ("a", 10)]
    assert extract([10, 20, 30], 2) == [20]


def test_extract2_and_use_series():
    data = RList([1, [2, 3], 4], ["a", "b", "c"])
    assert extract2(data, 2) == [2, 3]
    assert extract2(data, "b") == [2, 3]
    assert extract2(Vector([10, 20, 30], ["a", "b", "c"]), 2) == 20
    series = RList([1, [2, 3], 4], ["apple", "banana", "pear"])
    assert use_series(series, "banana") == [2, 3]
    with pytest.warns(UserWarning, match="partial match"):
        assert use_series(series, "ban") == [2, 3]
    with pytest.warns(UserWarning, match="multiple matches"):
        assert use_series(RList([1, 2], ["cat", "car"]), "c") is None
    assert use_series(RList([1, 2], ["b", "banana"]), "b") == 1
    with pytest.raises(IndexError, match="subscript out of bounds"):
        extract2([1, 2], 5)


def test_inset_and_inset2():
    original = Vector([1, 2, 3, 4], ["a", "b", "c", "d"])
    updated = inset(original, [2, 4], [20, 40])
    assert updated.pairs() == [("a", 1), ("b", 20), ("c", 3), ("d", 40)]
    assert original.values == [1, 2, 3, 4]
    assert inset([1, 2, 3, 4], [1, 3], 9) == [9, 2, 9, 4]
    listed = RList([1, 2, 3], ["a", "b", "c"])
    replaced = inset2(listed, 2, 99)
    assert replaced.pairs() == [("a", 1), ("b", 99), ("c", 3)]
    assert listed.values == [1, 2, 3]
    named = inset2(listed, "b", [7, 8])
    assert named.values[1] == [7, 8]


def test_names_class_and_attributes():
    assert set_names([1, 2, 3], ["a", "b", "c"]).pairs() == [("a", 1), ("b", 2), ("c", 3)]
    assert set_names([1, 2, 3, 4], "a").names == ["a", None, None, None]
    with pytest.raises(ValueError, match="names"):
        set_names([1, 2], ["a", "b", "c"])
    matrix = Matrix(list(range(1, 7)), nrow=2)
    named_cols = set_colnames(matrix, ["p", "q", "r"])
    assert named_cols.cells() == [[1, 3, 5], [2, 4, 6]]
    assert named_cols.colnames == ["p", "q", "r"]
    assert named_cols.rownames is None
    named_rows = set_rownames(matrix, ["u", "v"])
    assert named_rows.rownames == ["u", "v"]
    assert named_rows.colnames is None
    with pytest.raises(ValueError, match="dimnames"):
        set_colnames(matrix, ["p", "q"])
    classified = set_class([1, 2, 3], "myclass")
    assert classified.values == [1, 2, 3]
    assert classified.r_class == ["myclass"]
    colored = set_attr([1, 2, 3], "color", "red")
    assert colored.values == [1, 2, 3]
    assert colored.attributes == {"color": "red"}
    replaced = set_attributes(
        Vector([1, 2, 3], ["a", "b", "c"], {"color": "blue"}),
        {"names": ["a", "b", "c"], "color": "red"},
    )
    assert replaced.pairs() == [("a", 1), ("b", 2), ("c", 3)]
    assert replaced.attributes == {"color": "red"}
    cleared = set_attributes(colored, {"comment": "hi"})
    assert cleared.names is None
    assert cleared.attributes == {"comment": "hi"}


def test_matrix_linear_index_is_column_major():
    matrix = Matrix([1, 2, 3, 4, 5, 6], nrow=2)
    assert extract(matrix, 1) == 1
    assert extract(matrix, 2) == 2
    assert extract(matrix, 3) == 3
    assert extract(matrix, 2, [2, 3]) == [4, 6]


def test_warnings_filter_stays_quiet_for_the_matching_cases():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert divide_by_int(-7, 2) == -4
        assert mod(-7, 2) == 1
