use numpy::{Complex64, PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyList;
use std::cell::RefCell;
use std::slice;

#[repr(C)]
#[derive(Copy, Clone)]
struct FComplex {
    re: f64,
    im: f64,
}

type DerivFn = extern "C" fn(*mut i32, *mut f64, *mut FComplex, *mut FComplex);
type JacFn = unsafe extern "C" fn(
    *mut i32,
    *mut f64,
    *mut FComplex,
    *mut i32,
    *mut i32,
    *mut FComplex,
    *mut i32,
);

extern "C" {
    fn zvode_(
        f: unsafe extern "C" fn(
            *mut i32,
            *mut f64,
            *mut FComplex,
            *mut FComplex,
            *mut FComplex,
            *mut i32,
        ),
        neq: *mut i32,
        y: *mut FComplex,
        t: *mut f64,
        tout: *mut f64,
        itol: *mut i32,
        rtol: *mut f64,
        atol: *mut f64,
        itask: *mut i32,
        istate: *mut i32,
        iopt: *mut i32,
        zwork: *mut FComplex,
        lzw: *mut i32,
        rwork: *mut f64,
        lrw: *mut i32,
        iwork: *mut i32,
        liw: *mut i32,
        jac: unsafe extern "C" fn(
            *mut i32,
            *mut f64,
            *mut FComplex,
            *mut i32,
            *mut i32,
            *mut FComplex,
            *mut i32,
            *mut FComplex,
            *mut i32,
        ),
        mf: *mut i32,
        rpar: *mut FComplex,
        ipar: *mut i32,
    );
    fn zvode_set_callbacks(deriv: DerivFn, jac: JacFn);
    fn zvode_f(
        neq: *mut i32,
        t: *mut f64,
        y: *mut FComplex,
        ydot: *mut FComplex,
        rpar: *mut FComplex,
        ipar: *mut i32,
    );
    fn zvode_jac_dummy(
        neq: *mut i32,
        t: *mut f64,
        y: *mut FComplex,
        ml: *mut i32,
        mu: *mut i32,
        pd: *mut FComplex,
        nrowpd: *mut i32,
        rpar: *mut FComplex,
        ipar: *mut i32,
    );
}

thread_local! {
    static DERIV_FUNC: RefCell<Option<Py<PyAny>>> = RefCell::new(None);
    static JAC_FUNC: RefCell<Option<Py<PyAny>>> = RefCell::new(None);
}

fn fc_to_c64(value: FComplex) -> Complex64 {
    Complex64::new(value.re, value.im)
}

fn c64_to_fc(value: Complex64) -> FComplex {
    FComplex {
        re: value.re,
        im: value.im,
    }
}

fn py_to_complex(obj: &Bound<'_, PyAny>) -> PyResult<Complex64> {
    if let Ok(array) = obj.extract::<PyReadonlyArray1<Complex64>>() {
        let slice = array.as_slice()?;
        if slice.len() == 1 {
            return Ok(slice[0]);
        }
    }
    if obj.hasattr("imag")? {
        let real: f64 = obj.getattr("real")?.extract()?;
        let imag: f64 = obj.getattr("imag")?.extract()?;
        return Ok(Complex64::new(real, imag));
    }
    if let Ok(value) = obj.extract::<f64>() {
        return Ok(Complex64::new(value, 0.0));
    }
    Err(PyRuntimeError::new_err("expected a complex value"))
}

fn vec_complex_from_py(obj: &Bound<'_, PyAny>, n: usize) -> PyResult<Vec<FComplex>> {
    if let Ok(array) = obj.extract::<PyReadonlyArray1<Complex64>>() {
        let data = array.as_slice()?;
        if data.len() != n {
            return Err(PyRuntimeError::new_err(format!(
                "expected length {n}, got {}",
                data.len()
            )));
        }
        return Ok(data.iter().copied().map(c64_to_fc).collect());
    }
    if let Ok(list) = obj.cast::<PyList>() {
        if list.len() == 1 {
            if let Ok(inner) = list.get_item(0) {
                if let Ok(values) = vec_complex_from_py(inner.as_ref(), n) {
                    return Ok(values);
                }
            }
        }
        let mut out = Vec::with_capacity(n);
        for item in list.iter() {
            let c = py_to_complex(item.as_ref())?;
            out.push(c64_to_fc(c));
        }
        if out.len() != n {
            return Err(PyRuntimeError::new_err(format!(
                "expected length {n}, got {}",
                out.len()
            )));
        }
        return Ok(out);
    }
    let array = obj.extract::<PyReadonlyArray1<Complex64>>()?;
    let data = array.as_slice()?;
    if data.len() != n {
        return Err(PyRuntimeError::new_err(format!(
            "expected length {n}, got {}",
            data.len()
        )));
    }
    Ok(data.iter().copied().map(c64_to_fc).collect())
}

extern "C" fn rust_deriv(neq: *mut i32, t: *mut f64, y: *mut FComplex, ydot: *mut FComplex) {
    Python::attach(|py| {
        let n = unsafe { *neq } as usize;
        let time = unsafe { *t };
        let state: Vec<Complex64> = unsafe { slice::from_raw_parts(y, n) }
            .iter()
            .copied()
            .map(fc_to_c64)
            .collect();
        let func = DERIV_FUNC.with(|cell| cell.borrow().as_ref().map(|f| f.clone_ref(py)));
        let Some(func) = func else {
            return;
        };
        let y_obj = PyArray1::from_vec(py, state);
        let result = func.bind(py).call1((time, y_obj));
        let Ok(result) = result else { return };
        let Ok(values) = vec_complex_from_py(result.as_ref(), n) else {
            return;
        };
        let out = unsafe { slice::from_raw_parts_mut(ydot, n) };
        out.copy_from_slice(&values);
    });
}

extern "C" fn rust_jac_none(
    _neq: *mut i32,
    _t: *mut f64,
    _y: *mut FComplex,
    _ml: *mut i32,
    _mu: *mut i32,
    _pd: *mut FComplex,
    _nrowpd: *mut i32,
) {
}

extern "C" fn rust_jac(
    neq: *mut i32,
    t: *mut f64,
    y: *mut FComplex,
    ml: *mut i32,
    mu: *mut i32,
    pd: *mut FComplex,
    nrowpd: *mut i32,
) {
    Python::attach(|py| {
        let func = JAC_FUNC.with(|cell| cell.borrow().as_ref().map(|f| f.clone_ref(py)));
        let Some(func) = func else {
            return;
        };
        let n = unsafe { *neq } as usize;
        let time = unsafe { *t };
        let state: Vec<Complex64> = unsafe { slice::from_raw_parts(y, n) }
            .iter()
            .copied()
            .map(fc_to_c64)
            .collect();
        let y_obj = PyArray1::from_vec(py, state);
        let result = func.bind(py).call1((time, y_obj));
        let Ok(result) = result else { return };
        let nrow = unsafe { *nrowpd } as usize;
        let flat = if let Ok(list) = result.cast::<PyList>() {
            let mut vals = Vec::new();
            for row in list.iter() {
                if let Ok(row_list) = row.cast::<PyList>() {
                    for item in row_list.iter() {
                        let c = py_to_complex(item.as_ref()).unwrap_or(Complex64::new(0.0, 0.0));
                        vals.push(c64_to_fc(c));
                    }
                } else {
                    let c = py_to_complex(row.as_ref()).unwrap_or(Complex64::new(0.0, 0.0));
                    vals.push(c64_to_fc(c));
                }
            }
            vals
        } else if let Ok(array) = result.extract::<PyReadonlyArray1<Complex64>>() {
            array.as_slice().unwrap_or(&[]).iter().copied().map(c64_to_fc).collect()
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

fn compute_lzw(n: i32, maxord: i32, mf: i32, banddown: i32, bandup: i32) -> i32 {
    let mfa = mf.abs();
    let meth = mfa / 10;
    let miter = mfa - 10 * meth;
    let mut lzw = n * (maxord + 1) + 2 * n;
    if (miter == 1 || miter == 2) && mf > 0 {
        lzw += 2 * n * n + 2;
    }
    if (miter == 1 || miter == 2) && mf < 0 {
        lzw += n * n;
    }
    if miter == 3 {
        lzw += n;
    }
    if (miter == 4 || miter == 5) && mf > 0 {
        lzw += (3 * banddown + 2 * bandup + 2) * n;
    }
    if (miter == 4 || miter == 5) && mf < 0 {
        lzw += (2 * banddown + bandup + 1) * n;
    }
    lzw
}

fn compute_lrw(n: i32) -> i32 {
    20 + n
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
pub fn integrate_zvode(
    py: Python<'_>,
    y0: PyReadonlyArray1<Complex64>,
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
) -> PyResult<(Py<PyArray2<Complex64>>, Vec<i32>, Vec<f64>)> {
    let y_slice = y0.as_slice()?;
    let y_vec: Vec<FComplex> = y_slice.iter().copied().map(c64_to_fc).collect();
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

    let mut lzw = compute_lzw(n, maxord, mf, banddown, bandup);
    let mut lrw = compute_lrw(n);
    let mut liw = compute_liw(n, mf);

    let mut zwork = vec![FComplex { re: 0.0, im: 0.0 }; lzw as usize];
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

    let mut iopt = 0_i32;
    let step_controls = hini != 0.0 || hmax != 0.0 || hmin != 0.0 || maxsteps != 5000 || maxord != default_maxord;
    if step_controls {
        iopt = 1;
    }
    let mut itol = 1_i32;
    let mut rtol_v = [rtol; 1];
    let mut atol_v = [atol; 1];
    let mut itask = if tcrit.is_some() { 4 } else { 1 };
    let mut istate = 1_i32;
    let mut mf_i = mf;
    let mut rpar = [FComplex { re: 0.0, im: 0.0 }; 1];
    let mut ipar = [0_i32; 1];

    let has_jac = jacfunc.is_some();
    DERIV_FUNC.with(|cell| *cell.borrow_mut() = Some(func));
    JAC_FUNC.with(|cell| *cell.borrow_mut() = jacfunc);
    let jac_cb: JacFn = if has_jac { rust_jac } else { rust_jac_none };
    unsafe {
        zvode_set_callbacks(rust_deriv, jac_cb);
    }

    let mut n_eq = n;
    let ntot = n_eq;
    let row_len = ntot as usize + 1;
    let mut yout = vec![FComplex { re: 0.0, im: 0.0 }; row_len * nt];
    let mut xytmp = y_vec.clone();
    let mut tin = time_vec[0];
    yout[0] = FComplex {
        re: time_vec[0],
        im: 0.0,
    };
    for j in 0..n_eq as usize {
        yout[j + 1] = y_vec[j];
    }

    for it in 0..(nt - 1) {
        tin = time_vec[it];
        let mut tout = time_vec[it + 1];
        let mut repcount = 0;
        loop {
            unsafe {
                zvode_(
                    zvode_f,
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
                    zwork.as_mut_ptr(),
                    &mut lzw,
                    rwork.as_mut_ptr(),
                    &mut lrw,
                    iwork.as_mut_ptr(),
                    &mut liw,
                    zvode_jac_dummy,
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
        let base = (it + 1) * row_len;
        yout[base] = FComplex { re: tin, im: 0.0 };
        for j in 0..n_eq as usize {
            yout[base + j + 1] = xytmp[j];
        }
        if istate < 0 {
            break;
        }
    }

    DERIV_FUNC.with(|cell| *cell.borrow_mut() = None);
    JAC_FUNC.with(|cell| *cell.borrow_mut() = None);

    yout[0] = FComplex {
        re: time_vec[0],
        im: 0.0,
    };

    let mut istate_out = vec![0_i32; 21];
    istate_out[0] = istate;
    for k in 0..20 {
        istate_out[k + 1] = iwork[9 + k];
    }
    let rstate = vec![rwork[10], rwork[11], rwork[12], rwork[13], rwork[14]];

    let rows: Vec<Vec<Complex64>> = yout
        .chunks(row_len)
        .map(|chunk| chunk.iter().copied().map(fc_to_c64).collect())
        .collect();
    let array = PyArray2::from_vec2(py, &rows)?;
    Ok((array.into(), istate_out, rstate))
}

#[pymodule]
fn zvode(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(integrate_zvode, m)?)?;
    Ok(())
}
