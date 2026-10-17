use numpy::{PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyList;
use std::cell::RefCell;
use std::slice;

type DerivFn = extern "C" fn(*mut i32, *mut f64, *mut f64, *mut f64);
type JacFn = unsafe extern "C" fn(*mut i32, *mut f64, *mut f64, *mut i32, *mut i32, *mut f64, *mut i32);

extern "C" {
    fn dvode_(
        f: unsafe extern "C" fn(*mut i32, *mut f64, *mut f64, *mut f64, *mut f64, *mut i32),
        neq: *mut i32,
        y: *mut f64,
        t: *mut f64,
        tout: *mut f64,
        itol: *mut i32,
        rtol: *mut f64,
        atol: *mut f64,
        itask: *mut i32,
        istate: *mut i32,
        iopt: *mut i32,
        rwork: *mut f64,
        lrw: *mut i32,
        iwork: *mut i32,
        liw: *mut i32,
        jac: unsafe extern "C" fn(
            *mut i32,
            *mut f64,
            *mut f64,
            *mut i32,
            *mut i32,
            *mut f64,
            *mut i32,
        ),
        mf: *mut i32,
        rpar: *mut f64,
        ipar: *mut i32,
    );
    fn vode_set_callbacks(deriv: DerivFn, jac: JacFn);
    fn vode_f(
        neq: *mut i32,
        t: *mut f64,
        y: *mut f64,
        ydot: *mut f64,
        rpar: *mut f64,
        ipar: *mut i32,
    );
    fn vode_jac_dummy(
        neq: *mut i32,
        t: *mut f64,
        y: *mut f64,
        ml: *mut i32,
        mu: *mut i32,
        pd: *mut f64,
        nrowpd: *mut i32,
    );
}

thread_local! {
    static DERIV_FUNC: RefCell<Option<Py<PyAny>>> = RefCell::new(None);
    static JAC_FUNC: RefCell<Option<Py<PyAny>>> = RefCell::new(None);
}

fn vec_from_py(obj: &Bound<'_, PyAny>, n: usize) -> PyResult<Vec<f64>> {
    if let Ok(list) = obj.cast::<PyList>() {
        let mut out = Vec::with_capacity(n);
        for item in list.iter() {
            out.push(item.extract::<f64>()?);
        }
        if out.len() != n {
            return Err(PyRuntimeError::new_err(format!(
                "expected length {n}, got {}",
                out.len()
            )));
        }
        return Ok(out);
    }
    let array = obj.extract::<PyReadonlyArray1<f64>>()?;
    let data = array.as_slice()?.to_vec();
    if data.len() != n {
        return Err(PyRuntimeError::new_err(format!(
            "expected length {n}, got {}",
            data.len()
        )));
    }
    Ok(data)
}

extern "C" fn rust_deriv(neq: *mut i32, t: *mut f64, y: *mut f64, ydot: *mut f64) {
    Python::attach(|py| {
        let n = unsafe { *neq } as usize;
        let time = unsafe { *t };
        let state = unsafe { slice::from_raw_parts(y, n) }.to_vec();
        let func = DERIV_FUNC.with(|cell| cell.borrow().as_ref().map(|f| f.clone_ref(py)));
        let Some(func) = func else {
            return;
        };
        let y_obj = PyArray1::from_vec(py, state);
        let result = func.bind(py).call1((time, y_obj));
        let Ok(result) = result else { return };
        let Ok(values) = vec_from_py(result.as_ref(), n) else {
            return;
        };
        let out = unsafe { slice::from_raw_parts_mut(ydot, n) };
        out.copy_from_slice(&values);
    });
}

extern "C" fn rust_jac(
    neq: *mut i32,
    t: *mut f64,
    y: *mut f64,
    ml: *mut i32,
    mu: *mut i32,
    pd: *mut f64,
    nrowpd: *mut i32,
) {
    Python::attach(|py| {
        let func = JAC_FUNC.with(|cell| cell.borrow().as_ref().map(|f| f.clone_ref(py)));
        let Some(func) = func else {
            return;
        };
        let n = unsafe { *neq } as usize;
        let time = unsafe { *t };
        let state = unsafe { slice::from_raw_parts(y, n) }.to_vec();
        let y_obj = PyArray1::from_vec(py, state);
        let result = func.bind(py).call1((time, y_obj));
        let Ok(result) = result else { return };
        let nrow = unsafe { *nrowpd } as usize;
        let flat = if let Ok(list) = result.cast::<PyList>() {
            let mut vals = Vec::new();
            for row in list.iter() {
                if let Ok(row_list) = row.cast::<PyList>() {
                    for item in row_list.iter() {
                        vals.push(item.extract::<f64>().unwrap_or(0.0));
                    }
                } else {
                    vals.push(row.extract::<f64>().unwrap_or(0.0));
                }
            }
            vals
        } else if let Ok(array) = result.extract::<PyReadonlyArray1<f64>>() {
            array.as_slice().unwrap_or(&[]).to_vec()
        } else {
            return;
        };
        if flat.len() != nrow * n {
            return;
        }
        let out = unsafe { slice::from_raw_parts_mut(pd, nrow * n) };
        out.copy_from_slice(&flat);
        let _ = (ml, mu);
    });
}

fn compute_lrw(n: i32, maxord: i32, mf: i32, banddown: i32, bandup: i32) -> i32 {
    let mfa = mf.abs();
    let meth = mfa / 10;
    let miter = mfa - 10 * meth;
    let ml = banddown;
    let mu = bandup;
    let mut lrw = 20 + n * (maxord + 1) + 3 * n;
    if (miter == 1 || miter == 2) && mf > 0 {
        lrw += 2 * n * n + 2;
    }
    if (miter == 1 || miter == 2) && mf < 0 {
        lrw += n * n + 2;
    }
    if miter == 3 {
        lrw += n + 2;
    }
    if (miter == 4 || miter == 5) && mf > 0 {
        lrw += (3 * ml + 2 * mu + 2) * n + 2;
    }
    if (miter == 4 || miter == 5) && mf < 0 {
        lrw += (2 * ml + mu + 1) * n + 2;
    }
    lrw
}

fn compute_liw(n: i32, mf: i32) -> i32 {
    let mfa = mf.abs();
    let meth = mfa / 10;
    let miter = mfa - 10 * meth;
    if miter == 0 || miter == 3 {
        30
    } else {
        30 + n
    }
}

#[pyfunction]
#[pyo3(signature = (
    y0,
    times,
    func,
    *,
    mf=22,
    rtol=1e-6,
    atol=1e-6,
    maxord=None,
    maxsteps=5000,
    banddown=1,
    bandup=1,
    hini=0.0,
    hmax=0.0,
    hmin=0.0,
    tcrit=None,
    jacfunc=None
))]
pub fn integrate_vode(
    py: Python<'_>,
    y0: PyReadonlyArray1<f64>,
    times: PyReadonlyArray1<f64>,
    func: Py<PyAny>,
    mf: i32,
    rtol: f64,
    atol: f64,
    maxord: Option<i32>,
    maxsteps: i32,
    banddown: i32,
    bandup: i32,
    hini: f64,
    hmax: f64,
    hmin: f64,
    tcrit: Option<f64>,
    jacfunc: Option<Py<PyAny>>,
) -> PyResult<(Py<PyArray2<f64>>, Vec<i32>, Vec<f64>)> {
    let y_vec = y0.as_slice()?.to_vec();
    let time_vec = times.as_slice()?.to_vec();
    if time_vec.len() < 2 {
        return Err(PyRuntimeError::new_err("times must have length >= 2"));
    }
    let n = y_vec.len() as i32;
    let nt = time_vec.len();
    let mfa = mf.abs();
    let meth = mfa / 10;
    let default_maxord = if meth == 1 { 12 } else { 5 };
    let maxord = maxord.unwrap_or(default_maxord);

    let mut lrw = compute_lrw(n, maxord, mf, banddown, bandup);
    let mut liw = compute_liw(n, mf);

    let mut rwork = vec![0.0_f64; lrw as usize];
    let mut iwork = vec![0_i32; liw as usize];
    iwork[0] = banddown;
    iwork[1] = bandup;
    iwork[4] = maxord;
    iwork[5] = maxsteps;
    if let Some(tc) = tcrit {
        rwork[0] = tc;
    }
    rwork[4] = hini;
    rwork[5] = hmax;
    rwork[6] = hmin;

    let mut iopt = 1_i32;

    let mut itol = 1_i32;
    let mut rtol_v = [rtol; 1];
    let mut atol_v = [atol; 1];
    let mut itask = if tcrit.is_some() { 4 } else { 1 };
    let mut istate = 1_i32;
    let mut mf_i = mf;
    let mut rpar = [0.0_f64; 1];
    let mut ipar = [0_i32; 1];

    let has_jac = jacfunc.is_some();
    DERIV_FUNC.with(|cell| *cell.borrow_mut() = Some(func));
    JAC_FUNC.with(|cell| *cell.borrow_mut() = jacfunc);
    let jac_cb: JacFn = if has_jac { rust_jac } else { vode_jac_dummy };
    unsafe {
        vode_set_callbacks(rust_deriv, jac_cb);
    }

    let mut n_eq = n;
    let ntot = n_eq;
    let mut yout = vec![0.0_f64; (ntot as usize + 1) * nt];
    let mut xytmp = y_vec.clone();
    let mut tin = time_vec[0];
    yout[0] = tin;
    for j in 0..n_eq as usize {
        yout[j + 1] = y_vec[j];
    }

    for it in 0..(nt - 1) {
        tin = time_vec[it];
        let mut tout = time_vec[it + 1];
        let mut repcount = 0;
        loop {
            unsafe {
                dvode_(
                    vode_f,
                    &mut n_eq,
                    xytmp.as_mut_ptr(),
                    &mut tin,
                    &mut tout,
                    &mut itol,
                    rtol_v.as_mut_ptr(),
                    atol_v.as_mut_ptr(),
                    &mut itask,
                    &mut istate,
                    &mut iopt,
                    rwork.as_mut_ptr(),
                    &mut lrw,
                    iwork.as_mut_ptr(),
                    &mut liw,
                    vode_jac_dummy,
                    &mut mf_i,
                    rpar.as_mut_ptr(),
                    ipar.as_mut_ptr(),
                );
            }
            if istate == -2 {
                rtol_v[0] *= 10.0;
                atol_v[0] *= 10.0;
                istate = 3;
            }
            repcount += 1;
            if tin >= tout || istate < 0 || repcount >= 10 {
                break;
            }
        }
        if istate < 0 && istate != -1 {
            break;
        }
        let base = (it + 1) * (ntot as usize + 1);
        yout[base] = tin;
        for j in 0..n_eq as usize {
            yout[base + j + 1] = xytmp[j];
        }
        if istate < 0 {
            break;
        }
    }

    DERIV_FUNC.with(|cell| *cell.borrow_mut() = None);
    JAC_FUNC.with(|cell| *cell.borrow_mut() = None);

    yout[0] = time_vec[0];

    let mut istate_out = vec![0_i32; 21];
    istate_out[0] = istate;
    for k in 0..20 {
        istate_out[k + 1] = iwork[9 + k];
    }
    let rstate = vec![rwork[10], rwork[11], rwork[12], rwork[13], rwork[14]];

    let rows: Vec<Vec<f64>> = yout
        .chunks(ntot as usize + 1)
        .map(|chunk| chunk.to_vec())
        .collect();
    let array = PyArray2::from_vec2(py, &rows)?;
    Ok((array.into(), istate_out, rstate))
}

#[pymodule]
fn dvode(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(integrate_vode, m)?)?;
    Ok(())
}
