//! Aquaphy algal model derivatives, ported from deSolve `src/ex_Aquaphy.c`.

const NOUT: usize = 6;

/// Result of one aquaphy derivative evaluation (on-off PAR from day length).
#[derive(Debug, Clone, Copy)]
pub struct AquaphyEval {
    pub ydot: [f64; 4],
    pub out: [f64; NOUT],
}

fn eval_core(
    t: f64,
    y: &[f64; 4],
    parms: &[f64; 19],
    par: Option<f64>,
) -> AquaphyEval {
    let max_photo_synt = parms[0];
    let _r_mort_phy = parms[1];
    let alpha = parms[2];
    let p_exudation = parms[3];
    let max_protein_synt = parms[4];
    let ks_din = parms[5];
    let minp_lmw = parms[6];
    let maxp_lmw = parms[7];
    let min_quotum = parms[8];
    let max_storage = parms[9];
    let respiration_rate = parms[10];
    let p_resp = parms[11];
    let catabolism_rate = parms[12];
    let dilution_rate = parms[13];
    let r_nc_protein = parms[14];
    let input_din = parms[15];
    let r_chl_n = parms[16];
    let par_mean = parms[17];
    let day_length = parms[18];

    let din = y[0];
    let protein = y[1];
    let reserve = y[2];
    let lmw = y[3];

    let par = match par {
        Some(light) => light,
        None => {
            let hour_of_day = t.rem_euclid(24.0);
            if hour_of_day < day_length {
                par_mean
            } else {
                0.0
            }
        }
    };

    let phyto_c = protein + reserve + lmw;
    let phyto_n = protein * r_nc_protein;
    let nc_ratio = phyto_n / phyto_c;
    let chlorophyll = phyto_n * r_chl_n;
    let total_n = phyto_n + din;
    let chl_c_ratio = chlorophyll / phyto_c;

    let part_lmw = lmw / phyto_c;
    let mut limfac = ((maxp_lmw - part_lmw) / (maxp_lmw - minp_lmw)).min(1.0);
    limfac = limfac.max(0.0);
    let photo_synthesis = max_photo_synt
        * limfac
        * (1.0 - (alpha * par / max_photo_synt).exp())
        * protein;
    let exudation = p_exudation * photo_synthesis;
    let monod_quotum = (lmw / protein - min_quotum).max(0.0);
    let protein_synthesis =
        max_protein_synt * monod_quotum * din / (din + ks_din) * protein;
    let storage = max_storage * monod_quotum * protein;
    let respiration = respiration_rate * lmw + p_resp * protein_synthesis;
    let catabolism = catabolism_rate * reserve;

    let d_lmw = photo_synthesis + catabolism
        - exudation
        - storage
        - respiration
        - protein_synthesis
        - dilution_rate * lmw;
    let d_reserve = storage - catabolism - dilution_rate * reserve;
    let d_protein = protein_synthesis - dilution_rate * protein;
    let d_din = -protein_synthesis * r_nc_protein - dilution_rate * (din - input_din);

    AquaphyEval {
        ydot: [d_din, d_protein, d_reserve, d_lmw],
        out: [
            par,
            total_n,
            photo_synthesis,
            nc_ratio,
            chl_c_ratio,
            chlorophyll,
        ],
    }
}

/// On-off PAR (`par` is `None`) or forced light (`par` is `Some`).
pub fn aquaphy_eval(t: f64, y: &[f64; 4], parms: &[f64; 19], par: Option<f64>) -> AquaphyEval {
    eval_core(t, y, parms, par)
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyList};

    fn read4(y: PyReadonlyArray1<f64>) -> PyResult<[f64; 4]> {
        let slice = y
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        if slice.len() != 4 {
            return Err(PyValueError::new_err(
                "length of state variable vector should be 4",
            ));
        }
        Ok([slice[0], slice[1], slice[2], slice[3]])
    }

    fn read19(parms: PyReadonlyArray1<f64>) -> PyResult<[f64; 19]> {
        let slice = parms
            .as_slice()
            .map_err(|err| PyValueError::new_err(err.to_string()))?;
        if slice.len() != 19 {
            return Err(PyValueError::new_err(
                "length of parameter vector should be 19",
            ));
        }
        let mut out = [0.0; 19];
        out.copy_from_slice(slice);
        Ok(out)
    }

    #[pyfunction]
    #[pyo3(signature = (time, y, parms, par=None))]
    fn aquaphy_eval_py<'py>(
        py: Python<'py>,
        time: f64,
        y: PyReadonlyArray1<'py, f64>,
        parms: PyReadonlyArray1<'py, f64>,
        par: Option<f64>,
    ) -> PyResult<Bound<'py, PyDict>> {
        let state = read4(y)?;
        let p = read19(parms)?;
        let eval = crate::aquaphy_eval(time, &state, &p, par);
        let dict = PyDict::new(py);
        dict.set_item("delta", eval.ydot.to_vec().into_pyarray(py))?;
        dict.set_item("var", eval.out.to_vec().into_pyarray(py))?;
        Ok(dict)
    }

    #[pyfunction]
    fn aquaphy_pack_py<'py>(
        py: Python<'py>,
        times: Bound<'py, PyList>,
        y: PyReadonlyArray1<'py, f64>,
        parms: PyReadonlyArray1<'py, f64>,
        par: Option<f64>,
    ) -> PyResult<Bound<'py, PyList>> {
        let state = read4(y)?;
        let p = read19(parms)?;
        let out = PyList::empty(py);
        for item in times.iter() {
            let t: f64 = item.extract()?;
            let eval = crate::aquaphy_eval(t, &state, &p, par);
            for v in eval.ydot {
                out.append(v)?;
            }
            for v in eval.out {
                out.append(v)?;
            }
        }
        Ok(out)
    }

    #[pymodule]
    fn aquaphy(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(aquaphy_eval_py, m)?)?;
        m.add_function(wrap_pyfunction!(aquaphy_pack_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn day_length_switches_par() {
        let parms = [
            0.125, 0.001, -0.125 / 150.0, 0.0, 0.136, 1.0, 0.05, 0.15, 0.075, 0.23, 0.0001, 0.4,
            0.06, 0.01, 0.2, 10.0, 1.0, 250.0, 15.0,
        ];
        let y = [6.0, 20.0, 5.0, 1.0];
        let day = aquaphy_eval(10.0, &y, &parms, None);
        assert_eq!(day.out[0], 250.0);
        let night = aquaphy_eval(20.0, &y, &parms, None);
        assert_eq!(night.out[0], 0.0);
    }
}
