from mass import geyser


def test_geyser_has_the_mass_columns_and_rows():
    assert len(geyser["duration"]) == 299
    assert len(geyser["waiting"]) == 299
    assert geyser["waiting"][0] == 80
    assert geyser["duration"][0] == 4.0166667
