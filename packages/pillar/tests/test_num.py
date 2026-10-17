"""num() and set_num_opts() against pillar 1.11.1."""

import math

import pytest

from pillar.num import num, set_num_opts


def test_num_plain_vector_is_pillar_num():
    result = num([1, 2.5, None])
    assert result.data == [1.0, 2.5, None]
    assert result.pillar == "pillar_num"
    assert result.abbr == "num"
    assert result.classes == ("pillar_num", "pillar_vctr", "vctrs_vctr", "double")
    assert result.typeof == "double"
    assert result.notation is None


def test_integer_input_becomes_float():
    result = num([1, 2])
    assert result.data == [1.0, 2.0]
    assert result.data[0] == 1.0 and isinstance(result.data[0], float)
    assert num(1).data == [1.0]


def test_sigfig_label_and_sci_digits():
    labelled = num([1, 2], sigfig=4, label="kg")
    assert labelled.pillar == "pillar_num:4{kg}"
    assert labelled.abbr == "num:4"
    sci = num(1, digits=2, notation="sci")
    assert sci.pillar == "pillar_num(sci):.2!"
    assert sci.abbr == "sci:.2!"
    assert sci.data == [1.0]


def test_si_scale_and_exponent_skip_the_abbreviation():
    result = num(1, notation="si", fixed_exponent=-3, scale=10, label="m")
    assert result.pillar == "pillar_num(si){m}*10|-3"
    assert result.abbr == "si"


def test_digits_zero_and_negative_differ_for_the_abbreviation():
    zero = num(1, digits=0)
    assert zero.pillar == "pillar_num:.0!"
    assert zero.abbr == "num:.0"
    negative = num(1, digits=-2, notation="eng")
    assert negative.pillar == "pillar_num(eng):.2"
    assert negative.abbr == "eng:.2"
    whole = num(1, digits=2.0)
    assert whole.pillar == "pillar_num:.2!"
    assert whole.abbr == "num:.2!"


def test_extra_sigfig_star_is_only_on_the_full_type():
    marked = num(1, sigfig=3, extra_sigfig=True)
    assert marked.pillar == "pillar_num:3*"
    assert marked.abbr == "num:3"
    bare = num(1, extra_sigfig=True)
    assert bare.pillar == "pillar_num*"
    assert bare.abbr == "num"
    assert num(1, sigfig=3, extra_sigfig=False).pillar == "pillar_num:3"
    assert num(1, extra_sigfig=1).pillar == "pillar_num"


def test_digits_win_when_sigfig_is_also_set():
    result = num(1, sigfig=4, digits=2)
    assert result.pillar == "pillar_num:.2!"
    assert result.abbr == "num:.2!"


def test_numeric_rejections():
    with pytest.raises(ValueError, match=r"is\.numeric\(x\) is not TRUE"):
        num("a")
    with pytest.raises(ValueError, match=r"is\.numeric\(x\) is not TRUE"):
        num(True)
    with pytest.raises(ValueError, match=r"is\.numeric\(x\) is not TRUE"):
        num([True, False])
    with pytest.raises(ValueError, match=r"is\.numeric\(x\) is not TRUE"):
        num(None)


def test_notation_is_exact():
    assert num(1, notation="fit").pillar == "pillar_num(fit)"
    assert num(1, notation="eng").abbr == "eng"
    assert num(1, notation=None).pillar == "pillar_num"
    for prefix in ("f", "s", "e", "sc", "en"):
        with pytest.raises(ValueError) as exc:
            num(1, notation=prefix)
        assert str(exc.value) == (
            '`notation` must be one of "fit", "dec", "sci", "eng", or "si", '
            f'not "{prefix}".'
        )


def test_notation_type_errors():
    with pytest.raises(ValueError) as exc:
        num(1, notation=1)
    assert str(exc.value) == "`notation` must be a character vector, not the number 1."
    with pytest.raises(ValueError) as exc:
        num(1, notation=True)
    assert str(exc.value) == "`notation` must be a character vector, not `TRUE`."
    with pytest.raises(ValueError) as exc:
        num(1, notation=[])
    assert str(exc.value) == "`notation` must be length 1, not length 0"


def test_dec_fixed_exponent_uses_the_installed_spelling():
    with pytest.raises(ValueError) as exc:
        num(1, notation="dec", fixed_exponent=-2)
    assert str(exc.value) == (
        'Incomatible arguments: `notation = "dec"` and `fixed_exponent` given'
    )
    kept = num(1, notation="dec", fixed_exponent=0)
    assert kept.pillar == "pillar_num(dec)|0"
    assert num(1, notation="sci", fixed_exponent=0).pillar == "pillar_num(sci)|0"
    assert num(1, notation="dec", fixed_exponent=False).pillar == "pillar_num(dec)|FALSE"
    assert num(1, fixed_exponent=-3).pillar == "pillar_num|-3"


def test_scale_and_extra_sigfig_conflicts():
    with pytest.raises(ValueError) as exc:
        num(1, scale=10)
    assert str(exc.value) == "Must set `label` if `scale` is provided."
    with pytest.raises(ValueError) as exc:
        num(1, digits=2, extra_sigfig=True)
    assert str(exc.value) == "Incompatible arguments: `extra_sigfig` and `digits`."
    with pytest.raises(ValueError) as exc:
        num(1, digits=0, extra_sigfig=False)
    assert str(exc.value) == "Incompatible arguments: `extra_sigfig` and `digits`."


def test_digits_must_be_integerish():
    with pytest.raises(ValueError) as exc:
        num(1, digits=2.5)
    assert str(exc.value) == "is.null(digits) || is_integerish(digits) is not TRUE"
    with pytest.raises(ValueError) as exc:
        num(1, digits="2")
    assert str(exc.value) == "is.null(digits) || is_integerish(digits) is not TRUE"
    with pytest.raises(ValueError) as exc:
        num(1, digits=True)
    assert str(exc.value) == "is.null(digits) || is_integerish(digits) is not TRUE"
    with pytest.raises(ValueError) as exc:
        num(1, digits=2**53)
    assert str(exc.value) == "is.null(digits) || is_integerish(digits) is not TRUE"
    assert num(1, digits=2**52).pillar.endswith("!")


def test_nan_stays_nan_and_empty_is_a_double_vector():
    result = num([float("nan"), -0.0])
    assert math.isnan(result.data[0])
    assert math.copysign(1.0, result.data[1]) < 0
    empty = num([])
    assert empty.data == []
    assert empty.pillar == "pillar_num"
    assert empty.classes[0] == "pillar_num"


def test_set_num_opts_keeps_storage_and_formats_the_attribute():
    doubles = set_num_opts([1.0, 2.0], sigfig=2)
    assert doubles.data == [1.0, 2.0]
    assert doubles.pillar == "pillar_num:2"
    assert doubles.classes == ("numeric",)
    assert doubles.typeof == "double"
    assert doubles.abbr == "dbl"
    integers = set_num_opts([1, 2], sigfig=2)
    assert integers.data == [1, 2]
    assert all(isinstance(item, int) for item in integers.data)
    assert integers.pillar == "pillar_num:2"
    assert integers.classes == ("integer",)
    assert integers.typeof == "integer"
    assert integers.abbr == "int"


def test_set_num_opts_does_not_require_numeric_and_keeps_pillar_num():
    text = set_num_opts("a", sigfig=2)
    assert text.data == ["a"]
    assert text.classes == ("character",)
    assert text.pillar == "pillar_num:2"
    assert text.abbr == "chr"
    assert set_num_opts(True, sigfig=2).classes == ("logical",)
    base = num([1, 2], label="kg")
    updated = set_num_opts(base, sigfig=3, label="kg")
    assert updated.classes == base.classes
    assert updated.data == [1.0, 2.0]
    assert updated.pillar == "pillar_num:3{kg}"
    assert updated.abbr == "num:3"


def test_set_num_opts_shares_the_option_errors():
    with pytest.raises(ValueError) as exc:
        set_num_opts([1, 2], notation="dec", fixed_exponent=1)
    assert "Incomatible" in str(exc.value)
    with pytest.raises(ValueError, match="Must set `label`"):
        set_num_opts(1, scale=2)
    with pytest.raises(ValueError) as exc:
        set_num_opts(None, sigfig=2)
    assert str(exc.value) == "attempt to set an attribute on NULL"
    loose = set_num_opts(1, digits=2.5)
    assert loose.pillar == "pillar_num:.2.5!"
    character_digits = set_num_opts(1, digits="2")
    assert character_digits.pillar == "pillar_num:.2!"


def test_large_scale_uses_r_as_character():
    result = num(1, scale=1e5, label="m")
    assert result.pillar == "pillar_num{m}*1e+05"
