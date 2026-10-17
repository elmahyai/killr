//! nlme one-compartment model kernels from `nlme/src/nlme.c`.

const SL_INIT: f64 = f64::EPSILON;

fn is_na(x: f64) -> bool {
    x.is_nan()
}

/// Phenobarbital IV bolus model (`nlme_one_comp_first`).
pub fn one_comp_first(inmat: &[f64], nrow: usize) -> Result<Vec<f64>, String> {
    if inmat.len() != nrow * 5 {
        return Err(format!(
            "inmat must have length {} (5 columns), got {}",
            nrow * 5,
            inmat.len()
        ));
    }
    let mut resp = vec![0.0; nrow];
    let mut tl = vec![0.0; nrow];
    let mut ds = vec![0.0; nrow];
    let mut sl = SL_INIT;
    let mut mm = 0usize;

    for i in 0..nrow {
        let subject = inmat[i];
        let time = inmat[nrow + i];
        let dose = inmat[2 * nrow + i];
        let v = inmat[3 * nrow + i];
        let cl = inmat[4 * nrow + i];

        resp[i] = 0.0;
        if subject != sl {
            if is_na(dose) {
                return Err("First observation on an individual must have a dose".into());
            }
            sl = subject;
            mm = 0;
            tl[mm] = time;
            ds[mm] = dose;
        } else if !is_na(dose) {
            mm += 1;
            if mm >= nrow {
                return Err("too many doses for one subject".into());
            }
            tl[mm] = time;
            ds[mm] = dose;
        } else {
            let mut sum = 0.0;
            for j in 0..=mm {
                sum += ds[j] * (-cl * (time - tl[j]) / v).exp() / v;
            }
            resp[i] = sum;
        }
    }
    Ok(resp)
}

/// Quinidine oral absorption model (`nlme_one_comp_open`).
pub fn one_comp_open(inmat: &[f64], nrow: usize) -> Result<Vec<f64>, String> {
    if inmat.len() != nrow * 8 {
        return Err(format!(
            "inmat must have length {} (8 columns), got {}",
            nrow * 8,
            inmat.len()
        ));
    }
    let mut resp = vec![0.0; nrow];
    let mut sl = SL_INIT;
    let mut tl = 0.0;
    let mut c = 0.0;
    let mut ca = 0.0;

    for i in 0..nrow {
        let subject = inmat[i];
        let time = inmat[nrow + i];
        let conc = inmat[2 * nrow + i];
        let dose = inmat[3 * nrow + i];
        let interval = inmat[4 * nrow + i];
        let v = inmat[5 * nrow + i];
        let ka = inmat[6 * nrow + i];
        let ke = inmat[7 * nrow + i];

        if subject != sl {
            sl = subject;
            tl = time;
            resp[i] = 0.0;
            if !is_na(interval) {
                let interval = interval;
                c = dose
                    * ka
                    * (1.0 / (1.0 - (-ke * interval).exp())
                        - 1.0 / (1.0 - (-ka * interval).exp()))
                    / (v * (ka - ke));
                ca = dose / (v * (1.0 - (-ka * interval).exp()));
            } else {
                c = 0.0;
                ca = dose / v;
            }
        } else if !is_na(dose) {
            if !is_na(interval) {
                let interval = interval;
                c = dose
                    * ka
                    * (1.0 / (1.0 - (-ke * interval).exp())
                        - 1.0 / (1.0 - (-ka * interval).exp()))
                    / (v * (ka - ke));
                ca = dose / (v * (1.0 - (-ka * interval).exp()));
            } else {
                let delta = time - tl;
                c = c * (-ke * delta).exp()
                    + ca * ka * ((-ke * delta).exp() - (-ka * delta).exp()) / (ka - ke);
                ca = ca * (-ka * delta).exp() + dose / v;
            }
            tl = time;
            resp[i] = 0.0;
        } else if !is_na(conc) {
            let delta = time - tl;
            resp[i] = c * (-ke * delta).exp()
                + ca * ka * ((-ke * delta).exp() - (-ka * delta).exp()) / (ka - ke);
        } else {
            resp[i] = 0.0;
        }
    }
    Ok(resp)
}

#[cfg(feature = "python")]
mod python {
    use numpy::{PyReadonlyArray1, ToPyArray};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    fn flat_f64(arr: PyReadonlyArray1<f64>, expected: usize, label: &str) -> PyResult<Vec<f64>> {
        let slice = arr
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        if slice.len() != expected {
            return Err(PyValueError::new_err(format!(
                "{label} must have length {expected}, got {}",
                slice.len()
            )));
        }
        Ok(slice.to_vec())
    }

    #[pyfunction]
    #[pyo3(name = "one_comp_first")]
    fn one_comp_first_py<'py>(
        py: Python<'py>,
        inmat: PyReadonlyArray1<f64>,
        nrow: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let data = flat_f64(inmat, nrow * 5, "inmat")?;
        let out = crate::one_comp_first(&data, nrow).map_err(PyValueError::new_err)?;
        Ok(out.to_pyarray(py))
    }

    #[pyfunction]
    #[pyo3(name = "one_comp_open")]
    fn one_comp_open_py<'py>(
        py: Python<'py>,
        inmat: PyReadonlyArray1<f64>,
        nrow: usize,
    ) -> PyResult<Bound<'py, numpy::PyArray1<f64>>> {
        let data = flat_f64(inmat, nrow * 8, "inmat")?;
        let out = crate::one_comp_open(&data, nrow).map_err(PyValueError::new_err)?;
        Ok(out.to_pyarray(py))
    }

    #[pymodule]
    fn onecomp(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(one_comp_first_py, m)?)?;
        m.add_function(wrap_pyfunction!(one_comp_open_py, m)?)?;
        Ok(())
    }
}
