"""Canada checks against vars 1.6-1."""

import numpy as np

from vars import (
    BQ, Phi, SVAR, SVEC, VAR, VARselect, arch_test, causality, fevd, irf,
    logLik, normality_test, predict, restrict, roots, serial_test, vec2var, Canada,
)
from urca import ca_jo


def _fit():
    return VAR(Canada(), p=2)


def test_var_select_and_coefficients():
    data = Canada()
    assert data[0, 0] == np.float64("929.610513893698")
    selection = VARselect(data, lag_max=4)["selection"]
    assert list(selection) == [3, 2, 2, 3]
    fit = VAR(data, p=2)
    reference = np.array([
        1.6378206022874344, -0.17276581198201726, -0.26883287081837343,
        -0.58076381886552575, 0.16727166854706774, 1.1504282044123066,
        -0.081065001499198111, -0.078117073305600054,
    ])
    np.testing.assert_allclose(fit.coefficients.reshape(-1, order="F")[:8], reference, atol=1e-8)
    assert abs(logLik(fit)[0] - (-175.81856813700293)) < 1e-8
    modulus = np.sort(roots(fit))[::-1][:4]
    np.testing.assert_allclose(
        modulus,
        [0.99503376046265091, 0.90810617124788373, 0.90810617124788373, 0.73805647645545702],
        atol=1e-8,
    )


def test_dynamics_and_diagnostics():
    fit = _fit()
    np.testing.assert_allclose(
        Phi(fit, 3)[:, :, 1].reshape(-1, order="F")[:4],
        [1.6378206022874344, -0.17276581198201726, -0.26883287081837343, -0.58076381886552575],
        atol=1e-8,
    )
    np.testing.assert_allclose(
        fevd(fit, 3)[fit.names[0]].reshape(-1, order="F")[:6],
        [1, 0.96338150019054691, 0.89616924598821779, 0, 0.025630621676506971, 0.067971314605756381],
        atol=1e-8,
    )
    np.testing.assert_allclose(
        irf(fit, n_ahead=2, boot=False)[fit.names[0]].reshape(-1, order="F")[:6],
        [0.36281501944368877, 0.54753374684595457, 0.6179181392575448,
         -0.02058554058093643, -0.0012009465234657651, 0.014808435886315256],
        atol=1e-8,
    )
    np.testing.assert_allclose(
        predict(fit, n_ahead=2)["fcst"].reshape(-1, order="F"),
        [962.65568801863208, 963.65375596269803, 417.26230208573986, 417.74097754573313,
         470.29539604071067, 470.89482596382493, 6.4288323566271401, 5.9039185122823596],
        atol=1e-8,
    )
    assert abs(arch_test(fit, lags_multi=2)["statistic"] - 238.34937934900404) < 1e-8
    assert abs(serial_test(fit, lags_pt=4)["statistic"] - 56.208670704023639) < 1e-8
    assert abs(normality_test(fit)["statistic"] - 5.0940251899558637) < 1e-8


def test_causality_restrict_bq_svar():
    fit = _fit()
    out = causality(fit, cause="e")
    assert abs(out["Granger"]["statistic"] - 6.2768112264792606) < 1e-8
    assert abs(out["Instant"]["statistic"] - 26.068472087488125) < 1e-8
    pattern = restrict(fit, method="ser", thresh=2).restrictions.reshape(-1, order="F")
    expected = np.array([
        1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1,
        0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1,
    ])
    np.testing.assert_array_equal(pattern, expected)
    np.testing.assert_allclose(
        BQ(fit)["B"].reshape(-1, order="F")[:6],
        [-0.0076443197280391785, 0.54366334142189365, 0.08211180783151413,
         0.12945101708899009, -0.28469582169687052, 0.21657827645267647],
        atol=1e-8,
    )
    structural = np.eye(4)
    structural[np.tril_indices(4, -1)] = np.nan
    estimated = SVAR(fit, Bmat=structural)
    np.testing.assert_allclose(
        estimated["B"].reshape(-1, order="F")[:8],
        [1, -0.056738213858813509, -0.31981406619910152, -0.52483987975323765,
         0, 1, 0.14631215588291324, 0.023520500981756901],
        atol=1e-8,
    )


def test_vec2var_and_svec():
    data = Canada()
    joined = ca_jo(data, type="trace", ecdet="const", K=2, spec="longrun")
    level = vec2var(joined, r=1)
    np.testing.assert_allclose(
        level["A"][0].reshape(-1, order="F")[:6],
        [1.8066360919343447, -0.058567971065255096, -0.46785586407930363,
         -0.62672549796456811, 0.20843520793658324, 1.2758520823282449],
        atol=1e-8,
    )
    jo = ca_jo(data, ecdet="const", K=2)
    short_run = np.eye(4)
    short_run[np.tril_indices(4, -1)] = np.nan
    long_run = np.full((4, 4), np.nan)
    estimated = SVEC(jo, LR=long_run, SR=short_run, r=1, start=np.full(10, 0.1))
    np.testing.assert_allclose(
        estimated["SR"].reshape(-1, order="F")[:8],
        [0.38074397909267554, 0.047900059488954823, -0.10512941345025933,
         -0.20489299582017084, 0, 0.66821943261861472, 0.10880296489955199,
         0.011500616690191718],
        atol=1e-8,
    )
