"""Fixed cases checked against CRAN FNN 1.1.4.1."""

import numpy as np

from FNN import entropy, get_knn


def test_line_keeps_the_kd_tree_tie_order():
    data = np.column_stack([np.arange(1, 11), np.arange(1, 11)])
    found = get_knn(data, k=5)
    assert found["nn.index"][0].tolist() == [2, 3, 4, 5, 6]
    assert found["nn.index"][5].tolist() == [7, 5, 8, 4, 9]
    brute = get_knn(data, k=5, algorithm="brute")
    assert brute["nn.index"][5].tolist() == [5, 7, 4, 8, 3]


def test_correlation_keeps_the_earlier_tie():
    theta = np.linspace(0.1, 6, 10)
    circle = np.column_stack([np.cos(theta), np.sin(theta)])
    found = get_knn(circle, k=3, algorithm="CR")
    assert found["nn.index"][0].tolist() == [10, 2, 9]
    assert found["nn.index"][2].tolist() == [2, 4, 1]


def test_entropy_matches_the_line():
    data = np.column_stack([np.arange(1, 11), np.arange(1, 11)])
    got = entropy(data, k=3)
    expect = np.array([4.6668453203775995, 3.9441041926015776, 4.7153257247407563])
    assert np.max(np.abs(got - expect)) == 0.0
