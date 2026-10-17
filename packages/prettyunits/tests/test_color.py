import pytest

from prettyunits.color import pretty_color, pretty_colour


def test_pretty_color_matches_the_named_cases():
    black = pretty_color("black")
    assert black.name == "black"
    assert black.alt == ["black", "gray0", "grey0", "Black"]
    assert str(black) == "black"

    prussian = pretty_color("#123456")
    assert prussian.name == "Prussian Blue"
    assert prussian.alt == ["Prussian Blue"]

    missing = pretty_color(None)
    assert missing.name is None
    assert missing.alt is None
    assert str(missing) == "NA"


def test_pretty_colour_is_pretty_color():
    assert pretty_colour is pretty_color
    red = pretty_colour("#FF0000")
    assert red.name == "red"
    assert red.alt == ["red", "red1", "Red"]
    assert pretty_colour("black").name == "black"
    assert pretty_colour("black").alt == ["black", "gray0", "grey0", "Black"]


def test_col2rgb_forms():
    assert pretty_color("#F00").name == "red"
    assert pretty_color("#F00").alt == ["red", "red1", "Red"]
    assert pretty_color("#123").name == "Big Stone"
    assert pretty_color("#1234").alt == ["Big Stone"]
    assert pretty_color("GRAY").name == "gray"
    assert pretty_color(" grey").alt == ["gray", "grey"]
    assert pretty_color("transparent").name == "white"
    assert pretty_color("NA").alt == ["white", "gray100", "grey100", "White"]


def test_length_and_type_errors():
    with pytest.raises(ValueError, match=r"length\(color\) == 1 is not TRUE"):
        pretty_color(["black", "white"])
    with pytest.raises(ValueError, match=r"length\(color\) == 1 is not TRUE"):
        pretty_color(())
    with pytest.raises(ValueError, match="is.character\\(color\\) is not TRUE"):
        pretty_color(1)
    with pytest.raises(ValueError, match="is.character\\(color\\) is not TRUE"):
        pretty_color(["black"])
    with pytest.raises(ValueError, match="invalid color name"):
        pretty_color("notacolor")
    with pytest.raises(ValueError, match="invalid RGB specification"):
        pretty_color("#12345")
    with pytest.raises(ValueError, match="invalid hex digit"):
        pretty_color("#gg0000")
