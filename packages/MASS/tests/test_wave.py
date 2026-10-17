import math

import numpy as np
import pytest

from mass import (
    Null,
    area,
    as_fractions,
    bandwidth_nrd,
    con2tr,
    contr_sdif,
    enlist,
    fbeta,
    fractions,
    ginv,
    huber,
    hubers,
    is_fractions,
    kde2d,
    nclass_freq,
    rational,
    write_matrix,
)
from mass.errors import MassError


def test_huber_and_hubers_match_the_mass_sample():
    sample = [1, 2, 3, 4, 100]
    fitted = huber(sample)
    assert fitted["mu"] == pytest.approx(3.0559742835199999)
    assert fitted["s"] == pytest.approx(1.4825999999999999)
    both = hubers(sample)
    assert both["mu"] == pytest.approx(3.9609572454533635)
    assert both["s"] == pytest.approx(3.9134031941456398)
    with pytest.raises(MassError, match="MAD is zero"):
        huber([1, 1, 1])


def test_contrasts_ginv_and_null_match_r():
    matrix, _rows, names = contr_sdif(4)
    expected = np.array(
        [-0.75, 0.25, 0.25, 0.25, -0.5, -0.5, 0.5, 0.5, -0.25, -0.25, -0.25, 0.75]
    )
    assert matrix.ravel(order="F") == pytest.approx(expected)
    assert names == ["2-1", "3-2", "4-3"]
    grid = np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]])
    inverse = ginv(grid).ravel(order="F")
    assert inverse == pytest.approx(
        [
            -1.3333333333333344,
            -0.33333333333333404,
            0.66666666666666718,
            1.0833333333333346,
            0.33333333333333404,
            -0.4166666666666673,
        ]
    )
    basis = Null(np.column_stack([np.ones(4), np.arange(1, 5)])).ravel(order="F")
    assert basis[0] == pytest.approx(0.023606797749978925)
    with pytest.raises(MassError, match="numeric or complex matrix"):
        ginv(["a"])


def test_fractions_area_and_bandwidth():
    shown = fractions([0.5, 1 / 3, 2, math.pi])
    assert shown.fracs == ["1/2", "1/3", "2", "4272943/1360120"]
    assert rational([math.pi])[0] == pytest.approx(3.141592653589389)
    assert is_fractions(shown) is True
    assert is_fractions(0.5) is False
    assert as_fractions(1 / 7).fracs == ["1/7"]
    assert area(math.sin, 0, math.pi) == pytest.approx(2.0000000043235708)
    assert fbeta([0.3, 0.5], 2, 3) == pytest.approx([0.14699999999999996, 0.125])
    sample = [1, 2, 2, 3, 8, 9, 9, 10]
    assert bandwidth_nrd(sample) == pytest.approx(10.678221495457356)
    assert nclass_freq(sample) == 2
    copied = enlist({"a": 1, "b": 2.5})
    assert list(copied.values()) == [1, 2.5]
    stacked = con2tr(
        {"x": [1, 2], "y": [10, 20, 30], "z": np.array([[1, 3, 5], [2, 4, 6]], float)}
    )
    assert stacked["z"] == [1, 2, 3, 4, 5, 6]


def test_kde_and_write_matrix_match_r():
    density = kde2d([1, 1.2, 1.4, 2, 2.2], [3, 3.1, 2.8, 5, 5.2], n=5)
    assert density["z"].ravel(order="F")[0] == pytest.approx(0.21402699308647283)
    assert write_matrix([[1, 3.5], [2, 4]]) == "1.0 3.5\n2.0 4.0"
    named = write_matrix([[1, 0.001], [10, 100000]], columns=["a", "b"])
    assert named == "a b\n1e+00 1e-03\n1e+01 1e+05"
    with pytest.raises(MassError, match="same length"):
        kde2d([1, 2, 3], [1, 2])
