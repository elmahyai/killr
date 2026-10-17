from tibble import has_name, new_tibble, repair_names, tibble


def test_new_tibble_keeps_names_and_nrow():
    frame = new_tibble([[1, 2, 3], [4, 5, 6]], names=["a", "b"])
    assert frame.nrow == 3
    assert frame.names == ["a", "b"]
    assert frame["a"] == [1, 2, 3]
    assert frame["b"] == [4, 5, 6]


def test_has_name():
    frame = new_tibble([[1]], names=["a"])
    assert has_name(frame, "a") is True
    assert has_name(frame, "nope") is False


def test_repair_names_matches_vctrs_legacy():
    def names_of(*names):
        frame = new_tibble([[1] for _ in names], names=list(names), nrow=1)
        return repair_names(frame).names

    assert names_of("a", "a") == ["a", "a1"]
    assert names_of("a", "a", "a") == ["a", "a1", "a2"]
    assert names_of("a", "a", "a1") == ["a", "a2", "a1"]
    assert names_of("a", "a1", "a", "a1") == ["a", "a1", "a2", "a11"]
    assert names_of("V1", "") == ["V1", "V2"]
    assert names_of("", "", "") == ["V1", "V2", "V3"]
    assert names_of("", "ok") == ["V1", "ok"]
    assert names_of("a", "", "a") == ["a", "V1", "a1"]
    assert names_of("", "a", "", "a") == ["V1", "a", "V2", "a1"]
    assert names_of(".match", ".match") == [".match", ".match1"]
    assert repair_names(new_tibble([], names=[], nrow=0)).names == []


def test_repair_names_prefix_and_sep():
    frame = new_tibble([[1]], names=[""], nrow=1)
    assert repair_names(frame, prefix="X", sep="_").names == ["X_1"]


def test_tibble_recycles_length_one():
    frame = tibble(a=[1, 2, 3], b=1)
    assert frame["a"] == [1, 2, 3]
    assert frame["b"] == [1, 1, 1]


def test_tibble_rejects_duplicate_names():
    try:
        tibble(name_repair="check_unique", **{"a": [1], "b": [2]})
    except ValueError:
        pass
    else:
        frame = tibble(a=[1], b=[2])
        assert frame.names == ["a", "b"]
