"""The generator must match R 4.5 set.seed before any bootstrap is compared."""

from boot.rng import sample_int, set_seed, unif


def test_runif_matches_r_set_seed_1():
    set_seed(1)
    got = [unif() for _ in range(5)]
    expected = [
        0.26550866314209998,
        0.37212389963679016,
        0.57285336335189641,
        0.90820778999477625,
        0.2016819310374558,
    ]
    assert got == expected


def test_sample_int_replace_matches_r():
    set_seed(1)
    assert sample_int(10, 10, replace=True) == [9, 4, 7, 1, 2, 7, 2, 3, 1, 5]
    set_seed(2)
    assert sample_int(8, 8, replace=True) == [5, 7, 6, 6, 8, 8, 1, 5]


def test_sample_int_without_replacement_matches_r():
    set_seed(1)
    assert sample_int(5) == [1, 4, 3, 5, 2]
    set_seed(1)
    assert sample_int(10, 3) == [9, 4, 7]
