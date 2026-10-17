mod auto;
mod fixed;
mod util;

use auto::{rk_auto, ModelFunc, StepTimings};
use fixed::rk_fixed;
use util::set_istate_values;

pub struct SolveResult {
    pub yout: Vec<f64>,
    pub istate: [i32; 22],
    pub timesteps: [f64; 2],
}

struct CallbackModel<'a, F: FnMut(f64, &[f64], &mut [f64])> {
    f: &'a mut F,
}

impl<'a, F: FnMut(f64, &[f64], &mut [f64])> ModelFunc for CallbackModel<'a, F> {
    fn derivs(&mut self, t: f64, y: &[f64], ff: &mut [f64], stage_col: i32, neq: usize, _stage: usize) {
        if stage_col < 0 {
            return;
        }
        let col = stage_col as usize;
        let mut buf = vec![0.0; neq];
        (self.f)(t, y, &mut buf);
        for i in 0..neq {
            ff[i + neq * col] = buf[i];
        }
    }
}

#[allow(clippy::too_many_arguments)]
pub fn call_rk_auto<F: FnMut(f64, &[f64], &mut [f64])>(
    mut deriv: F,
    y0_in: &[f64],
    times: &[f64],
    stage: i32,
    fsal: i32,
    qerr: i32,
    a: &[f64],
    bb1: &[f64],
    bb2: &[f64],
    cc: &[f64],
    dd: Option<&[f64]>,
    densetype: i32,
    nknots_in: i32,
    alpha: f64,
    beta: f64,
    atol: &[f64],
    rtol: &[f64],
    tcrit: f64,
    hmin: f64,
    hmax: f64,
    hini: f64,
    maxsteps: i32,
    interpolate_all: bool,
) -> SolveResult {
    let neq = y0_in.len();
    let stage = stage as usize;
    let nt = times.len();
    let mut yout = vec![f64::NAN; nt * (neq + 1)];
    let mut istate = [0i32; 22];
    let mut timings = StepTimings { prev: 0.0, curr: 0.0 };

    let mut nknots = if nknots_in > 0 {
        nknots_in + 1
    } else {
        6
    };
    let mut interpolate = interpolate_all;
    if nknots < 2 {
        nknots = 1;
        interpolate = false;
    }
    if densetype > 0 {
        interpolate = true;
    }

    let dd_vec = dd.unwrap_or(&[]);
    let mut y0 = y0_in.to_vec();
    let mut y1 = vec![0.0; neq];
    let mut y2 = vec![0.0; neq];
    let mut dy1 = vec![0.0; neq];
    let mut dy2 = vec![0.0; neq];
    let mut ff = vec![0.0; neq * stage];
    let mut fj = vec![0.0; neq];
    let mut tmp = vec![0.0; neq];
    let mut rr = vec![0.0; neq * 5];
    let mut yknots = vec![0.0; (neq + 1) * (nknots as usize + 1)];

    yout[0] = times[0];
    yknots[0] = times[0];
    for i in 0..neq {
        yout[nt * (1 + i)] = y0[i];
    }
    let mut iknots = 1i32;
    for i in 0..neq {
        yknots[iknots as usize + (nknots as usize) * (1 + i)] = y0[i];
    }
    iknots += 1;

    let mut t = times[0];
    let tmax = times[nt - 1].max(tcrit);
    let mut dt = hmax.min(hini);
    let hmax_eff = hmax.min(tmax - t);
    let mut errold = 0.0;
    let mut it = 1i32;
    let mut it_ext = 0i32;
    let mut it_tot = 0i32;
    let mut it_rej = 0i32;

    let mut model = CallbackModel { f: &mut deriv };

    if interpolate {
        rk_auto(
            &mut model,
            fsal,
            neq,
            stage,
            0,
            nknots,
            true,
            densetype,
            maxsteps,
            nt,
            &mut iknots,
            &mut it,
            &mut it_ext,
            &mut it_tot,
            &mut it_rej,
            &mut istate,
            &mut t,
            tmax,
            hmin,
            hmax_eff,
            alpha,
            beta,
            &mut dt,
            &mut errold,
            times,
            &mut y0,
            &mut y1,
            &mut y2,
            &mut dy1,
            &mut dy2,
            &mut ff,
            &mut fj,
            &mut tmp,
            &mut rr,
            a,
            bb1,
            bb2,
            cc,
            dd_vec,
            atol,
            rtol,
            &mut yknots,
            &mut yout,
            &mut timings,
        );
    } else {
        for j in 0..(nt - 1) {
            t = times[j];
            let seg_max = times[j + 1].min(tcrit);
            dt = seg_max - t;
            rk_auto(
                &mut model,
                fsal,
                neq,
                stage,
                0,
                nknots,
                false,
                densetype,
                maxsteps,
                nt,
                &mut iknots,
                &mut it,
                &mut it_ext,
                &mut it_tot,
                &mut it_rej,
                &mut istate,
                &mut t,
                seg_max,
                hmin,
                hmax_eff,
                alpha,
                beta,
                &mut dt,
                &mut errold,
                times,
                &mut y0,
                &mut y1,
                &mut y2,
                &mut dy1,
                &mut dy2,
                &mut ff,
                &mut fj,
                &mut tmp,
                &mut rr,
                a,
                bb1,
                bb2,
                cc,
                dd_vec,
                atol,
                rtol,
                &mut yknots,
                &mut yout,
                &mut timings,
            );
            yout[j + 1] = seg_max;
            for i in 0..neq {
                yout[j + 1 + nt * (1 + i)] = y2[i];
            }
        }
    }

    set_istate_values(&mut istate, it_tot, stage as i32, fsal, qerr, it_rej);
    if densetype == 2 {
        istate[12] = it_tot * stage as i32 + 2;
    }

    SolveResult {
        yout,
        istate,
        timesteps: [timings.prev, timings.curr],
    }
}

#[allow(clippy::too_many_arguments)]
pub fn call_rk_fixed<F: FnMut(f64, &[f64], &mut [f64])>(
    mut deriv: F,
    y0_in: &[f64],
    times: &[f64],
    stage: i32,
    qerr: i32,
    a: &[f64],
    bb1: &[f64],
    cc: &[f64],
    nknots_in: i32,
    tcrit: f64,
    hini: f64,
    maxsteps: i32,
) -> SolveResult {
    let neq = y0_in.len();
    let stage = stage as usize;
    let nt = times.len();
    let mut yout = vec![f64::NAN; nt * (neq + 1)];
    let mut istate = [0i32; 22];
    let mut timings = StepTimings { prev: 0.0, curr: 0.0 };

    let mut nknots = if nknots_in > 0 {
        nknots_in + 1
    } else {
        6
    };
    let mut interpolate = true;
    if nknots < 2 {
        nknots = 1;
        interpolate = false;
    }

    let mut y0 = y0_in.to_vec();
    let mut y1 = vec![0.0; neq];
    let mut dy1 = vec![0.0; neq];
    let mut ff = vec![0.0; neq * stage];
    let mut fj = vec![0.0; neq];
    let mut tmp = vec![0.0; neq];
    let mut rr = vec![0.0; neq * 5];
    let mut yknots = vec![0.0; (neq + 1) * (nknots as usize + 1)];

    yout[0] = times[0];
    yknots[0] = times[0];
    for i in 0..neq {
        yout[nt * (1 + i)] = y0[i];
    }
    let mut iknots = 1i32;
    for i in 0..neq {
        yknots[iknots as usize + (nknots as usize) * (1 + i)] = y0[i];
    }
    iknots += 1;

    let mut t = times[0];
    let tmax = times[nt - 1].max(tcrit);
    let mut dt = 0.0;
    let mut it = 1i32;
    let mut it_ext = 0i32;
    let mut it_tot = 0i32;

    if hini > 0.0 {
        timings.curr = hini.min(times[1] - times[0]);
        timings.prev = timings.curr;
    } else {
        timings.curr = times[1] - times[0];
        timings.prev = timings.curr;
    }

    let mut model = CallbackModel { f: &mut deriv };

    if interpolate {
        rk_fixed(
            &mut model,
            neq,
            stage,
            0,
            nknots,
            true,
            maxsteps,
            nt,
            &mut iknots,
            &mut it,
            &mut it_ext,
            &mut it_tot,
            &mut istate,
            &mut t,
            tmax,
            hini,
            &mut dt,
            times,
            &mut y0,
            &mut y1,
            &mut dy1,
            &mut ff,
            &mut fj,
            &mut tmp,
            a,
            bb1,
            cc,
            &mut yknots,
            &mut yout,
            &mut timings,
        );
    } else {
        for j in 0..(nt - 1) {
            t = times[j];
            let seg_max = times[j + 1].min(tcrit);
            dt = seg_max - t;
            let h_step = hini.abs().min(dt.abs()) * util::sign(hini);
            rk_fixed(
                &mut model,
                neq,
                stage,
                0,
                nknots,
                false,
                maxsteps,
                nt,
                &mut iknots,
                &mut it,
                &mut it_ext,
                &mut it_tot,
                &mut istate,
                &mut t,
                seg_max,
                h_step,
                &mut dt,
                times,
                &mut y0,
                &mut y1,
                &mut dy1,
                &mut ff,
                &mut fj,
                &mut tmp,
                a,
                bb1,
                cc,
                &mut yknots,
                &mut yout,
                &mut timings,
            );
            yout[j + 1] = seg_max;
            for i in 0..neq {
                yout[j + 1 + nt * (1 + i)] = y1[i];
            }
        }
    }

    set_istate_values(&mut istate, it_tot, stage as i32, 0, qerr, 0);

    SolveResult {
        yout,
        istate,
        timesteps: [0.0, 0.0],
    }
}

#[cfg(feature = "python")]
mod python {
    use super::{call_rk_auto, call_rk_fixed};
    use numpy::{PyArray1, PyArray2, PyReadonlyArray1};
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::PySequence;

    fn first_derivative(result: Bound<'_, PyAny>, neq: usize) -> PyResult<Vec<f64>> {
        if let Ok(values) = result.extract::<Vec<f64>>() {
            if values.len() != neq {
                return Err(PyValueError::new_err("derivative length mismatch"));
            }
            return Ok(values);
        }
        let seq = result.cast::<PySequence>()?;
        let first = seq.get_item(0)?;
        let values: Vec<f64> = first.extract()?;
        if values.len() != neq {
            return Err(PyValueError::new_err("derivative length mismatch"));
        }
        Ok(values)
    }

    fn yout_to_matrix(yout: Vec<f64>, nt: usize, ncol: usize) -> Vec<f64> {
        let mut mat = vec![0.0; nt * ncol];
        for col in 0..ncol {
            for row in 0..nt {
                mat[row * ncol + col] = yout[row + nt * col];
            }
        }
        mat
    }

    #[pyfunction]
    #[pyo3(signature = (func, y0, times, *, varstep, stage, fsal, qerr, a, b1, b2=None, c, d=None, densetype=0, nknots=0, alpha, beta, atol, rtol, tcrit, hmin, hmax, hini, maxsteps))]
    fn rk_integrate<'py>(
        py: Python<'py>,
        func: Bound<'py, PyAny>,
        y0: PyReadonlyArray1<'py, f64>,
        times: PyReadonlyArray1<'py, f64>,
        varstep: bool,
        stage: i32,
        fsal: i32,
        qerr: i32,
        a: PyReadonlyArray1<'py, f64>,
        b1: PyReadonlyArray1<'py, f64>,
        b2: Option<PyReadonlyArray1<'py, f64>>,
        c: PyReadonlyArray1<'py, f64>,
        d: Option<PyReadonlyArray1<'py, f64>>,
        densetype: i32,
        nknots: i32,
        alpha: f64,
        beta: f64,
        atol: PyReadonlyArray1<'py, f64>,
        rtol: PyReadonlyArray1<'py, f64>,
        tcrit: f64,
        hmin: f64,
        hmax: f64,
        hini: f64,
        maxsteps: i32,
    ) -> PyResult<(Bound<'py, PyArray2<f64>>, Bound<'py, PyArray1<i32>>, [f64; 2])> {
        let y0_vec = y0.as_slice()?.to_vec();
        let times_vec = times.as_slice()?.to_vec();
        let neq = y0_vec.len();
        let nt = times_vec.len();
        if nt == 0 {
            return Err(PyValueError::new_err("times must be non-empty"));
        }
        let atol_vec = atol.as_slice()?.to_vec();
        let rtol_vec = rtol.as_slice()?.to_vec();
        let a_vec = a.as_slice()?.to_vec();
        let b1_vec = b1.as_slice()?.to_vec();
        let b2_vec = b2.map(|b| b.as_slice().map(|s| s.to_vec())).transpose()?;
        let c_vec = c.as_slice()?.to_vec();
        let d_vec = d.map(|v| v.as_slice().map(|s| s.to_vec())).transpose()?;

        let func_obj = func.clone().unbind();

        let mut closure = move |t: f64, y: &[f64], out: &mut [f64]| {
            Python::attach(|py| {
                let f = func_obj.bind(py);
                let y_arr = PyArray1::from_vec(py, y.to_vec());
                let ret = f.call((t, y_arr), None).expect("func call failed");
                let deriv = first_derivative(ret, neq).expect("bad derivative");
                out.copy_from_slice(&deriv);
            });
        };

        let result = if varstep {
            let bb2 = b2_vec.as_deref().unwrap_or(&[]);
            call_rk_auto(
                &mut closure,
                &y0_vec,
                &times_vec,
                stage,
                fsal,
                qerr,
                &a_vec,
                &b1_vec,
                bb2,
                &c_vec,
                d_vec.as_deref(),
                densetype,
                nknots,
                alpha,
                beta,
                &atol_vec,
                &rtol_vec,
                tcrit,
                hmin,
                hmax,
                hini,
                maxsteps,
                true,
            )
        } else {
            call_rk_fixed(
                &mut closure,
                &y0_vec,
                &times_vec,
                stage,
                qerr,
                &a_vec,
                &b1_vec,
                &c_vec,
                nknots,
                tcrit,
                hini,
                maxsteps,
            )
        };

        let ncol = neq + 1;
        let mat = yout_to_matrix(result.yout, nt, ncol);
        Ok((
            PyArray2::from_vec2(py, &mat.chunks(ncol).map(|row| row.to_vec()).collect::<Vec<_>>())?,
            PyArray1::from_slice(py, &result.istate),
            result.timesteps,
        ))
    }

    #[pymodule]
    fn rksolv(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(rk_integrate, m)?)?;
        Ok(())
    }
}
