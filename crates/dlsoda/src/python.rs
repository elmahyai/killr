use numpy::{PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyList;
use std::cell::RefCell;
use std::slice;

type DerivFn = extern "C" fn(*mut i32, *mut f64, *mut f64, *mut f64);
type JacFn = unsafe extern "C" fn(*mut i32, *mut f64, *mut f64, *mut i32, *mut i32, *mut f64, *mut i32);

extern "C" {
    fn dlsoda_(
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
            *mut f64,
            *mut i32,
        ),
        jt: *mut i32,
        rpar: *mut f64,
        ipar: *mut i32,
    );
    fn lsoda_set_callbacks(deriv: DerivFn, jac: JacFn);
    fn lsoda_f(
        neq: *mut i32,
        t: *mut f64,
        y: *mut f64,
        ydot: *mut f64,
        rpar: *mut f64,
        ipar: *mut i32,
    );
    fn lsoda_jac(
        neq: *mut i32,
        t: *mut f64,
        y: *mut f64,
        ml: *mut i32,
        mu: *mut i32,
        pd: *mut f64,
        nrowpd: *mut i32,
        rpar: *mut f64,
        ipar: *mut i32,
    );
    fn lsoda_jac_dummy(
        neq: *mut i32,
        t: *mut f64,
        y: *mut f64,
        ml: *mut i32,
        mu: *mut i32,
        pd: *mut f64,
        nrowpd: *mut i32,
        rpar: *mut f64,
        ipar: *mut i32,
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

extern "C" fn rust_jac_noop(
    _neq: *mut i32,
    _t: *mut f64,
    _y: *mut f64,
    _ml: *mut i32,
    _mu: *mut i32,
    _pd: *mut f64,
    _nrowpd: *mut i32,
) {
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

fn compute_lrw(n: i32, maxordn: i32, maxords: i32, jt: i32, banddown: i32, bandup: i32) -> i32 {
    let lmat = if jt == 1 || jt == 2 {
        n * n + 2
    } else {
        (2 * banddown + bandup + 1) * n + 2
    };
    let lrn = 20 + n * (maxordn + 1) + 3 * n;
    let lrs = 20 + n * (maxords + 1) + 3 * n + lmat;
    lrn.max(lrs)
}

#[pyfunction]
#[pyo3(signature = (
    y0,
    times,
    func,
    *,
    jt=2,
    rtol=1e-6,
    atol=1e-6,
    maxordn=12,
    maxords=5,
    maxsteps=5000,
    banddown=1,
    bandup=1,
    hini=0.0,
    hmax=0.0,
    hmin=0.0,
    tcrit=None,
    jacfunc=None
))]
pub fn integrate_lsoda(
    py: Python<'_>,
    y0: PyReadonlyArray1<f64>,
    times: PyReadonlyArray1<f64>,
    func: Py<PyAny>,
    jt: i32,
    rtol: f64,
    atol: f64,
    maxordn: i32,
    maxords: i32,
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

    let mut lrw = compute_lrw(n, maxordn, maxords, jt, banddown, bandup);
    let mut liw = 20 + n;

    let mut rwork = vec![0.0_f64; lrw as usize];
    let mut iwork = vec![0_i32; liw as usize];
    iwork[0] = banddown;
    iwork[1] = bandup;
    iwork[5] = maxsteps;
    if maxordn != 12 {
        iwork[7] = maxordn;
    }
    if maxords != 5 {
        iwork[8] = maxords;
    }
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
    let mut jt_i = jt;
    let mut rpar = [0.0_f64; 1];
    let mut ipar = [0_i32; 1];

    let has_jac = jacfunc.is_some();
    DERIV_FUNC.with(|cell| *cell.borrow_mut() = Some(func));
    JAC_FUNC.with(|cell| *cell.borrow_mut() = jacfunc);
    let jac_cb: JacFn = if has_jac { rust_jac } else { rust_jac_noop };
    unsafe {
        lsoda_set_callbacks(rust_deriv, jac_cb);
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

    let mut rows_written = 1usize;

    for _it in 0..(nt - 1) {
        tin = time_vec[_it];
        let mut tout = time_vec[_it + 1];
        let mut repcount = 0;
        loop {
            if istate == -2 {
                rtol_v[0] *= 10.0;
                atol_v[0] *= 10.0;
                istate = 3;
            }
            unsafe {
                dlsoda_(
                    lsoda_f,
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
                    if has_jac { lsoda_jac } else { lsoda_jac_dummy },
                    &mut jt_i,
                    rpar.as_mut_ptr(),
                    ipar.as_mut_ptr(),
                );
            }
            repcount += 1;
            if !(tin < tout && istate >= 0 && repcount < 10) {
                break;
            }
        }
        if istate == -3 {
            DERIV_FUNC.with(|cell| *cell.borrow_mut() = None);
            JAC_FUNC.with(|cell| *cell.borrow_mut() = None);
            return Err(PyRuntimeError::new_err(
                "illegal input detected before taking any integration steps - see written message",
            ));
        }
        let base = rows_written * (ntot as usize + 1);
        yout[base] = tin;
        for j in 0..n_eq as usize {
            yout[base + j + 1] = xytmp[j];
        }
        rows_written += 1;
        if istate < 0 || tin < tout {
            break;
        }
    }

    DERIV_FUNC.with(|cell| *cell.borrow_mut() = None);
    JAC_FUNC.with(|cell| *cell.borrow_mut() = None);

    yout[0] = time_vec[0];

    let mut istate_out = vec![0_i32; 21];
    istate_out[0] = istate;
    for k in 0..20 {
        istate_out[k + 1] = if k < iwork.len() { iwork[k] } else { 0 };
    }
    let rstate = vec![rwork[10], rwork[11], rwork[12], rwork[13], rwork[14]];

    let rows: Vec<Vec<f64>> = yout
        .chunks(ntot as usize + 1)
        .take(rows_written)
        .map(|chunk| chunk.to_vec())
        .collect();
    let array = PyArray2::from_vec2(py, &rows)?;
    Ok((array.into(), istate_out, rstate))
}

#[pymodule]
fn dlsoda(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(integrate_lsoda, m)?)?;
    Ok(())
}
