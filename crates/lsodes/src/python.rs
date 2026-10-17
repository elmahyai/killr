use numpy::{PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyList;
use std::cell::RefCell;
use std::os::raw::{c_double, c_int};
use std::slice;

type DerivFn = extern "C" fn(*mut c_int, *mut c_double, *mut c_double, *mut c_double, *mut c_double, *mut c_int);
type JacVecFn = extern "C" fn(
    *mut c_int,
    *mut c_double,
    *mut c_double,
    *mut c_int,
    *mut c_int,
    *mut c_int,
    *mut c_double,
    *mut c_double,
    *mut c_int,
);

extern "C" {
    fn lsodes_integrate(
        n: c_int,
        nt: c_int,
        y: *mut c_double,
        times: *mut c_double,
        yout: *mut c_double,
        istate21: *mut c_int,
        rstate5: *mut c_double,
        imp: c_int,
        maxord: c_int,
        maxsteps: c_int,
        nnz: c_int,
        liw_hint: c_int,
        lrw_hint: c_int,
        hini: c_double,
        hmax: c_double,
        hmin: c_double,
        tcrit: c_double,
        has_tcrit: c_int,
        rtol: *mut c_double,
        lrtol: c_int,
        atol: *mut c_double,
        latol: c_int,
        iwork_in: *mut c_int,
        liw: c_int,
        deriv: DerivFn,
        jacvec: JacVecFn,
    ) -> c_int;
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

extern "C" fn rust_deriv(
    neq: *mut c_int,
    t: *mut c_double,
    y: *mut c_double,
    ydot: *mut c_double,
    _rpar: *mut c_double,
    _ipar: *mut c_int,
) {
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

extern "C" fn rust_jacvec(
    neq: *mut c_int,
    t: *mut c_double,
    y: *mut c_double,
    j: *mut c_int,
    _ian: *mut c_int,
    _jan: *mut c_int,
    pdj: *mut c_double,
    _rpar: *mut c_double,
    _ipar: *mut c_int,
) {
    Python::attach(|py| {
        let func = JAC_FUNC.with(|cell| cell.borrow().as_ref().map(|f| f.clone_ref(py)));
        let Some(func) = func else {
            return;
        };
        let n = unsafe { *neq } as usize;
        let time = unsafe { *t };
        let col = unsafe { *j };
        let state = unsafe { slice::from_raw_parts(y, n) }.to_vec();
        let y_obj = PyArray1::from_vec(py, state);
        let result = func.bind(py).call1((time, y_obj, col));
        let Ok(result) = result else { return };
        let Ok(values) = vec_from_py(result.as_ref(), n) else {
            return;
        };
        let out = unsafe { slice::from_raw_parts_mut(pdj, n) };
        out.copy_from_slice(&values);
    });
}

extern "C" fn null_jacvec(
    _neq: *mut c_int,
    _t: *mut c_double,
    _y: *mut c_double,
    _j: *mut c_int,
    _ian: *mut c_int,
    _jan: *mut c_int,
    _pdj: *mut c_double,
    _rpar: *mut c_double,
    _ipar: *mut c_int,
) {
}

#[pyfunction]
#[pyo3(signature = (
    y0,
    times,
    func,
    *,
    imp=222,
    maxord=5,
    maxsteps=5000,
    nnz=None,
    rtol=1e-6,
    atol=1e-6,
    hini=0.0,
    hmax=0.0,
    hmin=0.0,
    tcrit=None,
    lrw=None,
    liw=None,
    iwork=None,
    jacvec=None,
))]
pub fn integrate_lsodes(
    py: Python<'_>,
    y0: PyReadonlyArray1<f64>,
    times: PyReadonlyArray1<f64>,
    func: Py<PyAny>,
    imp: i32,
    maxord: i32,
    maxsteps: i32,
    nnz: Option<i32>,
    rtol: f64,
    atol: f64,
    hini: f64,
    hmax: f64,
    hmin: f64,
    tcrit: Option<f64>,
    lrw: Option<i32>,
    liw: Option<i32>,
    iwork: Option<Vec<i32>>,
    jacvec: Option<Py<PyAny>>,
) -> PyResult<(Py<PyArray2<f64>>, Vec<i32>, Vec<f64>)> {
    let y_vec = y0.as_slice()?.to_vec();
    let mut time_vec = times.as_slice()?.to_vec();
    if time_vec.len() < 2 {
        return Err(PyRuntimeError::new_err("times must have length >= 2"));
    }
    let n = y_vec.len() as i32;
    let nt = time_vec.len() as i32;
    let nnz_val = nnz.unwrap_or(n * n);
    let lrw_hint = lrw.unwrap_or(0);
    let liw_hint = liw.unwrap_or(0);
    let mut iwork_buf = iwork.unwrap_or_else(|| vec![0; liw_hint.max(30) as usize]);
    if iwork_buf.len() < liw_hint.max(30) as usize {
        iwork_buf.resize(liw_hint.max(30) as usize, 0);
    }
    let liw_len = iwork_buf.len() as i32;

    let mut rtol_v = [rtol; 1];
    let mut atol_v = [atol; 1];
    let lrtol = 1_i32;
    let latol = 1_i32;

    let has_jac = jacvec.is_some();
    DERIV_FUNC.with(|cell| *cell.borrow_mut() = Some(func));
    JAC_FUNC.with(|cell| *cell.borrow_mut() = jacvec);
    let jac_cb: JacVecFn = if has_jac { rust_jacvec } else { null_jacvec };

    let mut yout = vec![0.0_f64; (n as usize + 1) * time_vec.len()];
    let mut istate21 = vec![0_i32; 21];
    let mut rstate5 = vec![0.0_f64; 5];
    let tc = tcrit.unwrap_or(0.0);
    let has_tcrit = if tcrit.is_some() { 1 } else { 0 };

    let mut y_mut = y_vec;
    let status = unsafe {
        lsodes_integrate(
            n,
            nt,
            y_mut.as_mut_ptr(),
            time_vec.as_mut_ptr(),
            yout.as_mut_ptr(),
            istate21.as_mut_ptr(),
            rstate5.as_mut_ptr(),
            imp,
            maxord,
            maxsteps,
            nnz_val,
            liw_hint,
            lrw_hint,
            hini,
            hmax,
            hmin,
            tc,
            has_tcrit,
            rtol_v.as_mut_ptr(),
            lrtol,
            atol_v.as_mut_ptr(),
            latol,
            iwork_buf.as_mut_ptr(),
            liw_len,
            rust_deriv,
            jac_cb,
        )
    };

    DERIV_FUNC.with(|cell| *cell.borrow_mut() = None);
    JAC_FUNC.with(|cell| *cell.borrow_mut() = None);

    istate21[0] = status;
    yout[0] = time_vec[0];

    let rows: Vec<Vec<f64>> = yout
        .chunks(n as usize + 1)
        .map(|chunk| chunk.to_vec())
        .collect();
    let array = PyArray2::from_vec2(py, &rows)?;
    Ok((array.into(), istate21, rstate5))
}

#[pymodule]
fn lsodes(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(integrate_lsodes, m)?)?;
    Ok(())
}
