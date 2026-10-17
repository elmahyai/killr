import numpy as np

from numderiv import genD, grad, hessian, jacobian


def test_grad_of_sin_matches_the_cosine_table():
    gradient = grad(np.sin, np.arange(11) * 2 * np.pi / 10)
    expected = np.array(
        [
            1,
            0.80901699436724894,
            0.30901699437215852,
            -0.3090169943735675,
            -0.80901699436884356,
            -0.99999999999338152,
            -0.80901699437029773,
            -0.3090169943733122,
            0.30901699437204233,
            0.80901699436918528,
            0.99999999999338118,
        ]
    )
    assert np.max(np.abs(gradient - expected)) == 0


def test_complex_step_of_sin_is_exact():
    assert grad(np.sin, np.pi, method="complex")[0] == -1


def test_one_sided_step_matches_the_published_value():
    assert grad(np.sin, -0.5, side=-1)[0] == 0.87758072705013257


def test_jacobian_is_the_column_major_matrix():
    def func2(x):
        return np.concatenate([np.sin(x), np.cos(x)])

    got = np.ravel(jacobian(func2, np.arange(2) * 2 * np.pi), order="F")
    expected = np.array([1, 0, 0, 0, 0, 0.99999999999338118, 0, 0])
    assert np.max(np.abs(got - expected)) == 0


def test_hessian_of_the_quadratic():
    def func(x):
        return x[0] ** 2 + 3 * x[0] * x[1] + x[1] ** 2

    got = hessian(func, [1.0, 1.0])
    expected = np.array(
        [
            [1.9999999999982325, 2.9999999999953282],
            [2.9999999999953282, 2.0000000000064451],
        ]
    )
    assert np.max(np.abs(got - expected)) == 0


def test_genD_matrix():
    def func(x):
        return np.array([x[0], x[0], x[1] ** 2])

    got = np.ravel(genD(func, [2.0, 2.0, 5.0])["D"], order="F")
    assert got[0] == 0.99999999999671463
    assert got[5] == 3.9999999999740266
    assert got[17] == 1.9999993047426492
