//! CCl4 inhalation model, ported from deSolve `src/ex_CCL4model.c`.

use std::sync::Mutex;

struct Derived {
    v: [f64; 5],
    p: [f64; 4],
    ai0: f64,
    q: [f64; 4],
    kl: f64,
    rats: f64,
    qp: f64,
    qc: f64,
    pb: f64,
    mw: f64,
    vmax: f64,
    km: f64,
}

static MODEL: Mutex<Option<Derived>> = Mutex::new(None);

/// Load primary parameters and compute derived quantities (`initccl4` / `derived`).
pub fn init_ccl4(parms: &[f64; 21]) -> Result<(), String> {
    let bw = parms[0];
    let qp = parms[1];
    let qc = parms[2];
    let vfc = parms[3];
    let vlc = parms[4];
    let vmc = parms[5];
    let qfc = parms[6];
    let qlc = parms[7];
    let qmc = parms[8];
    let pla = parms[9];
    let pfa = parms[10];
    let pma = parms[11];
    let pta = parms[12];
    let pb = parms[13];
    let mw = parms[14];
    let vmax = parms[15];
    let km = parms[16];
    let conc = parms[17];
    let kl = parms[18];
    let rats = parms[19];
    let vchc = parms[20];

    let vtc = 0.91 - (vlc + vfc + vmc);
    let v = [
        vchc - rats * bw,
        vmc * bw,
        vtc * bw,
        vfc * bw,
        vlc * bw,
    ];
    let ai0 = conc * v[0] * mw / 24450.0;
    let p = [pma / pb, pta / pb, pfa / pb, pla / pb];
    let q = [
        qmc * qc,
        qc - (qmc * qc + qlc * qc + qfc * qc),
        qfc * qc,
        qlc * qc,
    ];

    let derived = Derived {
        v,
        p,
        ai0,
        q,
        kl,
        rats,
        qp,
        qc,
        pb,
        mw,
        vmax,
        km,
    };
    *MODEL
        .lock()
        .map_err(|_| "ccl4model state lock poisoned".to_string())? = Some(derived);
    Ok(())
}

/// Model derivatives and outputs (`derivsccl4`).
pub fn derivs_ccl4(_t: f64, y: &[f64; 7]) -> Result<( [f64; 7], [f64; 3]), String> {
    let model = MODEL
        .lock()
        .map_err(|_| "ccl4model state lock poisoned".to_string())?;
    let m = model
        .as_ref()
        .ok_or_else(|| "call init_ccl4 before derivs_ccl4".to_string())?;

    let mut tconc = [0.0; 5];
    for i in 0..5 {
        tconc[i] = y[i] / m.v[i];
    }

    let mut vconc = [0.0; 5];
    vconc[0] = 0.0;
    for i in 1..5 {
        vconc[i] = tconc[i] / m.p[i - 1];
        vconc[0] += vconc[i] * m.q[i - 1] / m.qc;
    }

    let ca = (m.qc * vconc[0] + m.qp * tconc[0]) / (m.qc + m.qp / m.pb);
    let cx = ca / m.pb;
    let ram = m.vmax * vconc[4] / (m.km + vconc[4]);

    let mut ydot = [0.0; 7];
    ydot[0] = m.rats * m.qp * (cx - tconc[0]) - m.kl * y[0];
    for i in 1..5 {
        ydot[i] = m.q[i - 1] * (ca - vconc[i]);
    }
    ydot[4] -= ram;
    ydot[5] = tconc[4];
    ydot[6] = ram;

    let out = [
        m.ai0 - y[0],
        (y[1] + y[2] + y[3] + y[4] + y[6]) * m.rats,
        tconc[0] * 24450.0 / m.mw,
    ];
    Ok((ydot, out))
}

#[cfg(feature = "python")]
mod py {
    use numpy::{PyReadonlyArray1, ToPyArray};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    fn parms_array(parms: PyReadonlyArray1<f64>) -> PyResult<[f64; 21]> {
        let slice = parms
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        if slice.len() != 21 {
            return Err(PyValueError::new_err(
                "length of parameter vector should be 21",
            ));
        }
        let mut out = [0.0; 21];
        out.copy_from_slice(slice);
        Ok(out)
    }

    fn state_array(y: PyReadonlyArray1<f64>) -> PyResult<[f64; 7]> {
        let slice = y
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        if slice.len() != 7 {
            return Err(PyValueError::new_err(
                "length of state variable vector should be 7",
            ));
        }
        let mut out = [0.0; 7];
        out.copy_from_slice(slice);
        Ok(out)
    }

    #[pyfunction]
    #[pyo3(name = "init_ccl4")]
    fn init_ccl4_py(parms: PyReadonlyArray1<f64>) -> PyResult<()> {
        crate::init_ccl4(&parms_array(parms)?).map_err(PyValueError::new_err)
    }

    #[pyfunction]
    #[pyo3(name = "derivs_ccl4")]
    fn derivs_ccl4_py<'py>(
        py: Python<'py>,
        t: f64,
        y: PyReadonlyArray1<f64>,
    ) -> PyResult<(Bound<'py, numpy::PyArray1<f64>>, Bound<'py, numpy::PyArray1<f64>>)> {
        let (ydot, out) = crate::derivs_ccl4(t, &state_array(y)?).map_err(PyValueError::new_err)?;
        Ok((ydot.to_pyarray(py), out.to_pyarray(py)))
    }

    #[pymodule]
    fn ccl4model(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(init_ccl4_py, m)?)?;
        m.add_function(wrap_pyfunction!(derivs_ccl4_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn example_parms() -> [f64; 21] {
        [
            0.182, 4.0, 4.0, 0.08, 0.04, 0.74, 0.05, 0.15, 0.32, 16.17, 281.48, 13.3, 16.17, 5.487,
            153.8, 0.04321671, 0.4027255, 1000.0, 0.02, 1.0, 3.8,
        ]
    }

    #[test]
    fn init_and_derivs_run() {
        init_ccl4(&example_parms()).unwrap();
        let y = [21.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        let (ydot, out) = derivs_ccl4(0.0, &y).unwrap();
        assert_eq!(ydot.len(), 7);
        assert_eq!(out.len(), 3);
    }
}
