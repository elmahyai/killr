"""Checks against rootSolve 1.8.2.4 for the steady-state solvers."""

import matplotlib.pyplot as plt
import numpy as np
import pytest

from rootSolve import (
    image_steady2d,
    image_steady3d,
    multiroot,
    multiroot_1d,
    plot_steady1d,
    runsteady,
    steady,
    steady_1d,
    steady_2d,
    steady_3d,
    steady_band,
    stode,
    stodes,
    subset_steady2d,
    summary_rootsolve,
)

TOLERANCE = 1e-8


def circle(x):
    return [x[0] ** 2 + x[1] ** 2 - 1, x[0] ** 2 - x[1] ** 2 + 0.5]


def cubic(x):
    return [
        x[0] + x[1] + x[2] ** 2 - 12,
        x[0] ** 2 - x[1] + x[2] - 2,
        2 * x[0] - x[1] ** 2 + x[2] - 1,
    ]


def exchange(time, y, parms):
    return [[-0.1 * y[0] + 0.02 * y[1], 0.1 * y[0] - 0.2 * y[1]]]


def decay(time, y, parms):
    return [[-0.1 * value for value in y]]


def chain(time, y, parms):
    n = len(y)
    rate = [0.0] * n
    rate[0] = y[1] - y[0]
    for index in range(1, n - 1):
        rate[index] = y[index - 1] - 2 * y[index] + y[index + 1]
    rate[n - 1] = 1 - y[n - 1]
    return [rate]


def diffusion(time, y, parms):
    grid = np.asarray(y.values, dtype=float).reshape((3, 3), order="F")
    change = np.zeros_like(grid)
    for row in range(3):
        for col in range(3):
            left = 0.0 if row == 0 else grid[row - 1, col]
            right = 1.0 if row == 2 else grid[row + 1, col]
            down = 0.0 if col == 0 else grid[row, col - 1]
            up = 0.0 if col == 2 else grid[row, col + 1]
            change[row, col] = left + right + down + up - 4 * grid[row, col]
    return [change.reshape(-1, order="F")]


def approach(time, y, parms):
    return [[1.0 - value for value in y]]


def test_multiroot_matches_both_newton_paths():
    fortran = multiroot(circle, [1.0, 1.0])
    plain = multiroot(circle, [1.0, 1.0], useFortran=False)
    target = np.array([0.50000002323223014, 0.8660254037839501])
    assert np.max(np.abs(np.asarray(fortran.root.values) - target)) < TOLERANCE
    assert np.max(np.abs(np.asarray(plain.root.values) - target)) < TOLERANCE
    assert fortran.iter == 5
    assert plain.iter == 5
    assert abs(fortran.estim_precis - 2.3232230639269602e-08) < TOLERANCE


def test_multiroot_three_equations():
    found = multiroot(cubic, [1.0, 1.0, 1.0])
    target = np.array([
        1.0000000054474631, 2.0000000044922408, 2.9999999983917589,
    ])
    assert np.max(np.abs(np.asarray(found.root.values) - target)) < TOLERANCE
    assert found.iter == 6


def test_stode_and_steady_match_the_exchange_model():
    solved = stode([1.0, 1.0], func=exchange)
    target = np.array([-3.6103087186489802e-09, -2.0683321722003711e-09])
    assert np.max(np.abs(np.asarray(solved.y.values) - target)) < TOLERANCE
    assert solved.precis[0] == pytest.approx(0.09)
    assert solved.steady is True
    dispatched = steady([1.0, 2.0], func=exchange)
    other = np.array([-2.0683317281111613e-09, -1.5701487665609193e-08])
    assert np.max(np.abs(np.asarray(dispatched.y.values) - other)) < TOLERANCE
    assert dispatched.classes[0] == "steady"
    assert dispatched.nspec == 2


def test_banded_decay_matches():
    solved = steady_band([1.0, 2.0, 3.0, 4.0], func=decay, nspec=1)
    target = np.array([
        -5.2635584779636702e-10,
        -1.052711695592734e-09,
        -2.9334644491285644e-08,
        -2.1054233911854681e-09,
    ])
    assert np.max(np.abs(np.asarray(solved.y.values) - target)) < TOLERANCE
    assert solved.precis[0] == pytest.approx(0.25)


def test_stodes_matches_stode_on_the_chain():
    start = [0.2] * 5
    sparse = stodes(start, func=chain)
    dense = stode(start, func=chain)
    # R's sparse factorisation sits 9.3e-9 from this Newton on the same start.
    r_sparse = np.array([
        0.99999998667732437, 0.99999998667732437, 0.99999998667732415,
        0.99999998667732393, 1.0,
    ])
    assert np.max(np.abs(np.asarray(sparse.y.values) - r_sparse)) < TOLERANCE
    assert np.max(np.abs(
        np.asarray(sparse.y.values) - np.asarray(dense.y.values)
    )) < TOLERANCE


def test_steady_1d_and_multiroot_1d():
    start = [0.2] * 5
    solved = steady_1d(start, func=chain, nspec=1)
    target = np.full(5, 0.99999999598019262)
    assert np.max(np.abs(np.asarray(solved.y.values) - target)) < TOLERANCE
    assert solved.classes[0] == "steady1D"
    assert solved.dimens == 5
    found = multiroot_1d(lambda x: chain(0, x, None)[0], start, nspec=1)
    assert np.max(np.abs(np.asarray(found.root.values) - target)) < TOLERANCE
    assert found.iter == 2


def test_steady_2d_and_3d():
    solved = steady_2d([0.2] * 9, func=diffusion, dimens=(3, 3), nspec=1)
    target = np.array([
        0.071428572394883205, 0.18750000197864683, 0.42857142880632426,
        0.098214286966472872, 0.25000000318445664, 0.52678571499128646,
        0.071428572564107257, 0.18750000265554304, 0.42857143078957338,
    ])
    assert np.max(np.abs(np.asarray(solved.y.values) - target)) < TOLERANCE
    assert solved.classes[0] == "steady2D"
    cube = steady_3d([0.0] * 8, func=approach, dimens=(2, 2, 2))
    assert np.max(np.abs(np.asarray(cube.y.values) - 0.99999999497524072)) < TOLERANCE
    assert cube.dimens == [2, 2, 2]


def test_runsteady_stops_at_the_tolerance_crossing():
    solved = runsteady([0.0], func=approach, times=[0, np.inf])
    assert abs(solved.y.values[0] - 0.9999999901088259) < TOLERANCE
    assert solved.steady is True


def test_summary_matches_the_two_dimensional_quartiles():
    solved = steady_2d(
        [0.2] * 9, func=diffusion, dimens=(3, 3), nspec=1, names=["A"],
    )
    frame = summary_rootsolve(solved)
    target = {
        "Min.": 0.071428572394883205,
        "1st Qu.": 0.098214286966472872,
        "Median": 0.18750000265554304,
        "Mean": 0.25000000159236602,
        "3rd Qu.": 0.42857142880632426,
        "Max.": 0.52678571499128646,
        "N": 9,
        "sd": 0.17139601609235608,
    }
    for name, value in target.items():
        assert frame.columns["A"][name] == pytest.approx(value, abs=TOLERANCE)


def test_plot_draws_the_grid_and_the_state():
    solved = steady_1d([0.2] * 5, func=chain, nspec=1)
    drawn = plot_steady1d(solved)
    try:
        series = drawn.coordinates[0]
        assert np.allclose(series["x"], [1, 2, 3, 4, 5])
        assert np.max(np.abs(series["y"] - 0.99999999598019262)) < TOLERANCE
        assert len(drawn.figure.axes[0].lines) == 1
    finally:
        plt.close(drawn.figure)


def test_image_and_subset_use_the_column_major_matrix():
    solved = steady_2d(
        [0.2] * 9, func=diffusion, dimens=(3, 3), nspec=1, names=["A"],
    )
    block = subset_steady2d(solved, which=1)
    assert block.shape == (3, 3)
    assert np.max(np.abs(
        np.ravel(block, order="F") - np.asarray(solved.y.values)
    )) == 0.0
    drawn = image_steady2d(solved, which=1)
    try:
        item = drawn.coordinates[0]
        assert np.allclose(item["x"], [0.0, 0.5, 1.0])
        assert np.allclose(item["y"], [0.0, 0.5, 1.0])
        assert np.max(np.abs(
            np.ravel(item["z"], order="F") - np.asarray(solved.y.values)
        )) == 0.0
    finally:
        plt.close(drawn.figure)


def test_image_3d_slices_the_last_dimension():
    cube = steady_3d([0.0] * 8, func=approach, dimens=(2, 2, 2))
    drawn = image_steady3d(cube, which=1)
    try:
        assert len(drawn.coordinates) == 2
        assert drawn.coordinates[0]["z"].shape == (2, 2)
        assert np.max(np.abs(drawn.coordinates[0]["z"] - 0.99999999497524072)) < TOLERANCE
    finally:
        plt.close(drawn.figure)


def test_solver_errors_match_the_r_text():
    with pytest.raises(ValueError, match="either nspec or dimens"):
        steady_1d([0.0, 1.0], func=exchange)
    with pytest.raises(ValueError, match="dll or shared library"):
        stode([0.0], func="derivs")
    with pytest.raises(ValueError, match="method"):
        steady([0.0], func=approach, method="ode")
    with pytest.raises(ValueError, match="Can only select one"):
        solved = steady_2d([0.2] * 9, func=diffusion, dimens=(3, 3), nspec=1)
        # one species, which of two indices
        subset_steady2d(solved, which=[1, 1])
