"""pwr 1.3-0 examples against R."""

import math

import pytest

from pwr import (
    ES_h,
    ES_w1,
    ES_w2,
    cohen_ES,
    plot_power_htest,
    pwr_2p2n_test,
    pwr_2p_test,
    pwr_anova_test,
    pwr_chisq_test,
    pwr_f2_test,
    pwr_norm_test,
    pwr_p_test,
    pwr_r_test,
    pwr_t2n_test,
    pwr_t_test,
)
from pwr._stats import PwrError


def test_effect_sizes():
    assert ES_h(0.5, 0.4) == pytest.approx(0.20135792079033088, abs=1e-8)
    p0 = [0.25, 0.25, 0.25, 0.25]
    p1 = [0.375, (1 - 0.375) / 3, (1 - 0.375) / 3, (1 - 0.375) / 3]
    assert ES_w1(p0, p1) == pytest.approx(0.28867513459481287, abs=1e-8)
    prob = [[0.225, 0.125, 0.125, 0.125], [0.16, 0.16, 0.04, 0.04]]
    assert ES_w2(prob) == pytest.approx(0.2558646068639514, abs=1e-8)
    assert cohen_ES(test="r", size="medium")["effect.size"] == 0.3


def test_power_examples():
    assert pwr_t_test(d=2 / 2.8, n=30)["power"] == pytest.approx(0.7764888766441721, abs=1e-8)
    assert pwr_t_test(d=0.2, n=60, sig_level=0.10, type="one.sample")["power"] == pytest.approx(
        0.45558176408398932, abs=1e-8
    )
    paired = 8 / (16 * math.sqrt(2 * (1 - 0.6)))
    assert pwr_t_test(d=paired, n=40, type="paired")["power"] == pytest.approx(0.93152482532092973, abs=1e-8)
    assert pwr_t2n_test(d=0.6, n1=90, n2=60, alternative="greater")["power"] == pytest.approx(
        0.97372615462921719, abs=1e-8
    )
    assert pwr_p_test(h=ES_h(0.5, 0.4), n=60)["power"] == pytest.approx(0.34470140912721536, abs=1e-8)
    assert pwr_2p_test(h=0.3, n=80, alternative="greater")["power"] == pytest.approx(0.59967770454643765, abs=1e-8)
    assert pwr_2p2n_test(h=0.30, n1=80, n2=245, alternative="greater")["power"] == pytest.approx(
        0.75329244723188638, abs=1e-8
    )
    assert pwr_chisq_test(w=0.289, df=3, N=100)["power"] == pytest.approx(0.6750776570037208, abs=1e-8)
    assert pwr_r_test(r=0.3, n=50)["power"] == pytest.approx(0.57155584186020802, abs=1e-8)
    assert pwr_r_test(r=0.3, n=50, alternative="less")["r"] == pytest.approx(-0.3, abs=1e-8)
    assert pwr_anova_test(f=0.28, k=4, n=20)["power"] == pytest.approx(0.5149792921968589, abs=1e-8)
    assert pwr_norm_test(d=(105 - 100) / 15, n=20, alternative="greater")["power"] == pytest.approx(
        0.43874902754101119, abs=1e-8
    )
    assert pwr_f2_test(u=5, v=89, f2=0.1 / 0.9)["power"] == pytest.approx(0.67358577091439897, abs=1e-8)


def test_solved_sample_size_and_curve():
    assert pwr_t_test(d=0.3, power=0.75, alternative="greater")["n"] == pytest.approx(120.22320169891204, abs=1e-8)
    result = pwr_t_test(d=0.3, power=0.8, type="two.sample")
    curve = plot_power_htest(result, draw=False)
    assert len(curve["sample_sizes"]) == 21
    assert curve["power"][0] == pytest.approx(0.09742459135297421, abs=1e-8)
    assert curve["power"][-1] == pytest.approx(0.92981738690500415, abs=1e-8)


def test_missing_argument_and_class():
    with pytest.raises(PwrError, match="exactly one"):
        pwr_t_test(d=0.5)
    with pytest.raises(PwrError, match="power.htest"):
        plot_power_htest({"n": 10})
