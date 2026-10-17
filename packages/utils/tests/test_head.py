"""head() and tail() against R 4.5.0."""

import pytest

from utils.head import RMatrix, UtilsError, checkHT, head, tail


def test_vector_ends():
    values = list(range(1, 11))
    assert head(values) == [1, 2, 3, 4, 5, 6]
    assert tail(values) == [5, 6, 7, 8, 9, 10]
    assert head(values, -2) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert tail(values, -2) == [3, 4, 5, 6, 7, 8, 9, 10]


def test_matrix_slice_and_labels():
    matrix = RMatrix(list(range(1, 13)), 4, 3)
    top = head(matrix, 2)
    assert top.data == [1, 2, 5, 6, 9, 10]
    bottom = tail(matrix, 2)
    assert bottom.data == [3, 4, 7, 8, 11, 12]
    assert bottom.dimnames == [["[3,]", "[4,]"], None]
    wide = tail(RMatrix(list(range(1, 21)), 10, 2), 2)
    assert wide.dimnames[0] == [" [9,]", "[10,]"]


def test_check_ht_rejects_an_empty_n():
    checkHT(6, None)
    with pytest.raises(UtilsError, match="got none"):
        checkHT([], None)
