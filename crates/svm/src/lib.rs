//! LIBSVM from e1071 `src/svm.cpp`, train/predict from `src/Rsvm.c`.

#[link(name = "svm_kernel", kind = "static")]
#[link(name = "e1071_svm_wrapper", kind = "static")]
#[link(name = "stdc++")]
extern "C" {
    fn e1071_svm_set_cv_seed(seed: u64);
    fn e1071_svm_train(
        x: *mut f64,
        r: *mut i32,
        c: *mut i32,
        y: *mut f64,
        rowindex: *mut i32,
        colindex: *mut i32,
        svm_type: *mut i32,
        kernel_type: *mut i32,
        degree: *mut i32,
        gamma: *mut f64,
        coef0: *mut f64,
        cost: *mut f64,
        nu: *mut f64,
        weightlabels: *mut i32,
        weights: *mut f64,
        nweights: *mut i32,
        cache: *mut f64,
        tolerance: *mut f64,
        epsilon: *mut f64,
        shrinking: *mut i32,
        cross: *mut i32,
        sparse: *mut i32,
        probability: *mut i32,
        nclasses: *mut i32,
        nr: *mut i32,
        index: *mut i32,
        labels: *mut i32,
        nsv: *mut i32,
        rho: *mut f64,
        coefs: *mut f64,
        sigma: *mut f64,
        proba: *mut f64,
        probb: *mut f64,
        cresults: *mut f64,
        ctotal1: *mut f64,
        ctotal2: *mut f64,
        error: *mut i8,
        error_len: i32,
    );
    fn e1071_svm_predict(
        decisionvalues: i32,
        probability: i32,
        v: *mut f64,
        r: *mut i32,
        c: *mut i32,
        rowindex: *mut i32,
        colindex: *mut i32,
        coefs: *mut f64,
        rho: *mut f64,
        compprob: i32,
        proba: *mut f64,
        probb: *mut f64,
        nclasses: *mut i32,
        totnsv: *mut i32,
        labels: *mut i32,
        nsv: *mut i32,
        sparsemodel: *mut i32,
        svm_type: *mut i32,
        kernel_type: *mut i32,
        degree: *mut i32,
        gamma: *mut f64,
        coef0: *mut f64,
        x: *mut f64,
        xr: *mut i32,
        xrowindex: *mut i32,
        xcolindex: *mut i32,
        sparsex: *mut i32,
        ret: *mut f64,
        dec: *mut f64,
        prob: *mut f64,
    );
}

#[cfg(feature = "python")]
mod py {
    use numpy::{IntoPyArray, PyReadonlyArray1};
    use pyo3::exceptions::{PyRuntimeError, PyValueError};
    use pyo3::prelude::*;
    use pyo3::types::PyDict;

    use crate::{e1071_svm_predict, e1071_svm_set_cv_seed, e1071_svm_train};

    fn owned_f64(array: &PyReadonlyArray1<'_, f64>) -> PyResult<Vec<f64>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    fn owned_i32(array: &PyReadonlyArray1<'_, i32>) -> PyResult<Vec<i32>> {
        if let Ok(slice) = array.as_slice() {
            return Ok(slice.to_vec());
        }
        Ok(array.as_array().iter().copied().collect())
    }

    #[pyfunction]
    #[pyo3(name = "set_cv_seed")]
    fn set_cv_seed_py(seed: u64) {
        unsafe { e1071_svm_set_cv_seed(seed) };
    }

    #[pyfunction]
    #[pyo3(name = "train", signature = (
        x,
        y,
        *,
        svm_type=0,
        kernel_type=2,
        degree=3,
        gamma=0.1,
        coef0=0.0,
        cost=1.0,
        nu=0.5,
        weight_labels=None,
        weights=None,
        cachesize=40.0,
        tolerance=0.001,
        epsilon=0.1,
        shrinking=true,
        cross=0,
        sparse=false,
        probability=false,
    ))]
    fn train_py<'py>(
        py: Python<'py>,
        x: PyReadonlyArray1<'py, f64>,
        y: PyReadonlyArray1<'py, f64>,
        svm_type: i32,
        kernel_type: i32,
        degree: i32,
        gamma: f64,
        coef0: f64,
        cost: f64,
        nu: f64,
        weight_labels: Option<PyReadonlyArray1<'py, i32>>,
        weights: Option<PyReadonlyArray1<'py, f64>>,
        cachesize: f64,
        tolerance: f64,
        epsilon: f64,
        shrinking: bool,
        cross: i32,
        sparse: bool,
        probability: bool,
    ) -> PyResult<Bound<'py, PyDict>> {
        let mut x = owned_f64(&x)?;
        let y = owned_f64(&y)?;
        let mut nr = y.len() as i32;
        if nr == 0 {
            return Err(PyValueError::new_err("empty training data"));
        }
        if x.len() % y.len() != 0 {
            return Err(PyValueError::new_err("length of x must be a multiple of length of y"));
        }
        let mut nc = (x.len() / y.len()) as i32;

        let (mut weight_labels_vec, mut weights_vec, mut nweights) = match (weight_labels, weights) {
            (Some(wl), Some(w)) => {
                let wl_vec = owned_i32(&wl)?;
                let w = owned_f64(&w)?;
                if wl_vec.len() != w.len() {
                    return Err(PyValueError::new_err("weight_labels and weights must match"));
                }
                let n = wl_vec.len() as i32;
                (wl_vec, w, n)
            }
            (None, None) => (Vec::new(), Vec::new(), 0),
            _ => {
                return Err(PyValueError::new_err(
                    "weight_labels and weights must both be set or both omitted",
                ));
            }
        };

        let mut rowindex = vec![0i32; 1];
        let mut colindex = vec![0i32; 1];
        let mut svm_type = svm_type;
        let mut kernel_type = kernel_type;
        let mut degree = degree;
        let mut gamma = gamma;
        let mut coef0 = coef0;
        let mut cost = cost;
        let mut nu = nu;
        let mut cache = cachesize;
        let mut tol = tolerance;
        let mut eps = epsilon;
        let mut shrink = i32::from(shrinking);
        let mut cross = cross;
        let mut sparse_flag = i32::from(sparse);
        let mut prob_flag = i32::from(probability);

        let mut nclasses = 0i32;
        let mut nsv_total = 0i32;
        let mut index = vec![0i32; nr as usize];
        let mut labels = vec![0i32; nr as usize];
        let mut nsv = vec![0i32; nr as usize];
        let max_pairs = (nr * (nr - 1) / 2).max(1) as usize;
        let mut rho = vec![0.0; max_pairs];
        let mut coefs = vec![0.0; (nr as usize) * (nr as usize).max(1)];
        let mut sigma = 0.0;
        let mut proba = vec![0.0; max_pairs];
        let mut probb = vec![0.0; max_pairs];
        let mut cresults = vec![0.0; cross.max(0) as usize];
        let mut ctotal1 = 0.0;
        let mut ctotal2 = 0.0;
        let mut error = vec![0i8; 256];

        unsafe {
            e1071_svm_train(
                x.as_mut_ptr(),
                &mut nr,
                &mut nc,
                y.as_ptr() as *mut f64,
                rowindex.as_mut_ptr(),
                colindex.as_mut_ptr(),
                &mut svm_type,
                &mut kernel_type,
                &mut degree,
                &mut gamma,
                &mut coef0,
                &mut cost,
                &mut nu,
                weight_labels_vec.as_mut_ptr(),
                weights_vec.as_mut_ptr(),
                &mut nweights,
                &mut cache,
                &mut tol,
                &mut eps,
                &mut shrink,
                &mut cross,
                &mut sparse_flag,
                &mut prob_flag,
                &mut nclasses,
                &mut nsv_total,
                index.as_mut_ptr(),
                labels.as_mut_ptr(),
                nsv.as_mut_ptr(),
                rho.as_mut_ptr(),
                coefs.as_mut_ptr(),
                &mut sigma,
                proba.as_mut_ptr(),
                probb.as_mut_ptr(),
                cresults.as_mut_ptr(),
                &mut ctotal1,
                &mut ctotal2,
                error.as_mut_ptr(),
                error.len() as i32,
            );
        }

        let err = unsafe {
            std::ffi::CStr::from_ptr(error.as_ptr() as *const i8)
                .to_str()
                .unwrap_or("")
        };
        if !err.is_empty() {
            return Err(PyRuntimeError::new_err(format!("{err}!")));
        }

        index.truncate(nsv_total as usize);
        labels.truncate(nclasses as usize);
        nsv.truncate(nclasses as usize);
        let npairs = (nclasses * (nclasses - 1) / 2) as usize;
        rho.truncate(npairs);
        coefs.truncate((nsv_total as usize) * ((nclasses - 1).max(0) as usize));

        let dict = PyDict::new(py);
        dict.set_item("nclasses", nclasses)?;
        dict.set_item("tot_nsv", nsv_total)?;
        dict.set_item("index", index.into_pyarray(py))?;
        dict.set_item("labels", labels.into_pyarray(py))?;
        dict.set_item("nSV", nsv.into_pyarray(py))?;
        dict.set_item("rho", rho.into_pyarray(py))?;
        dict.set_item("coefs", coefs.into_pyarray(py))?;
        dict.set_item("sigma", sigma)?;
        if probability {
            proba.truncate(npairs);
            probb.truncate(npairs);
            dict.set_item("probA", proba.into_pyarray(py))?;
            dict.set_item("probB", probb.into_pyarray(py))?;
        }
        if cross > 0 {
            dict.set_item("cresults", cresults.into_pyarray(py))?;
            dict.set_item("ctotal1", ctotal1)?;
            dict.set_item("ctotal2", ctotal2)?;
        }
        Ok(dict)
    }

    #[pyfunction]
    #[pyo3(name = "predict", signature = (
        model_sv,
        coefs,
        rho,
        x,
        *,
        tot_nsv,
        sv_nc,
        svm_type=0,
        kernel_type=2,
        degree=3,
        gamma=0.1,
        coef0=0.0,
        nclasses=2,
        labels,
        nsv,
        compprob=false,
        prob_a=None,
        prob_b=None,
        sparse_model=false,
        decision_values=false,
        probability=false,
    ))]
    fn predict_py<'py>(
        py: Python<'py>,
        model_sv: PyReadonlyArray1<'py, f64>,
        coefs: PyReadonlyArray1<'py, f64>,
        rho: PyReadonlyArray1<'py, f64>,
        x: PyReadonlyArray1<'py, f64>,
        mut tot_nsv: i32,
        sv_nc: i32,
        svm_type: i32,
        kernel_type: i32,
        degree: i32,
        gamma: f64,
        coef0: f64,
        nclasses: i32,
        labels: PyReadonlyArray1<'py, i32>,
        nsv: PyReadonlyArray1<'py, i32>,
        compprob: bool,
        prob_a: Option<PyReadonlyArray1<'py, f64>>,
        prob_b: Option<PyReadonlyArray1<'py, f64>>,
        sparse_model: bool,
        decision_values: bool,
        probability: bool,
    ) -> PyResult<Bound<'py, PyDict>> {
        let mut sv = owned_f64(&model_sv)?;
        let coefs = owned_f64(&coefs)?;
        let mut rho = owned_f64(&rho)?;
        let mut test = owned_f64(&x)?;
        let labels = owned_i32(&labels)?;
        let nsv = owned_i32(&nsv)?;

        if sv_nc <= 0 || tot_nsv <= 0 {
            return Err(PyValueError::new_err("tot_nsv and sv_nc must be positive"));
        }
        if sv.len() != tot_nsv as usize * sv_nc as usize {
            return Err(PyValueError::new_err("model_sv length does not match tot_nsv * sv_nc"));
        }
        let mut sv_nr = tot_nsv;
        let mut sv_nc_mut = sv_nc;

        let mut xr = (test.len() / sv_nc as usize) as i32;
        if xr <= 0 || test.len() != xr as usize * sv_nc as usize {
            return Err(PyValueError::new_err("x length must be nrow * sv_nc"));
        }

        let mut proba = prob_a.map(|a| owned_f64(&a)).transpose()?.unwrap_or_default();
        let mut probb = prob_b.map(|b| owned_f64(&b)).transpose()?.unwrap_or_default();

        let mut ret = vec![0.0; xr as usize];
        let dec_len = if decision_values {
            xr as usize * (nclasses * (nclasses - 1) / 2) as usize
        } else {
            0
        };
        let mut dec = vec![0.0; dec_len];
        let mut prob = vec![0.0; xr as usize * nclasses as usize];

        let mut rowindex = vec![0i32; 1];
        let mut colindex = vec![0i32; 1];
        let mut xrowindex = vec![0i32; 1];
        let mut xcolindex = vec![0i32; 1];
        let mut svm_type = svm_type;
        let mut kernel_type = kernel_type;
        let mut degree = degree;
        let mut gamma = gamma;
        let mut coef0 = coef0;
        let mut nclasses = nclasses;
        let mut sparse_model = i32::from(sparse_model);
        let mut sparsex = 0i32;

        unsafe {
            e1071_svm_predict(
                i32::from(decision_values),
                i32::from(probability),
                sv.as_mut_ptr(),
                &mut sv_nr,
                &mut sv_nc_mut,
                rowindex.as_mut_ptr(),
                colindex.as_mut_ptr(),
                coefs.as_ptr() as *mut f64,
                rho.as_mut_ptr(),
                i32::from(compprob),
                proba.as_mut_ptr(),
                probb.as_mut_ptr(),
                &mut nclasses,
                &mut tot_nsv,
                labels.as_ptr() as *mut i32,
                nsv.as_ptr() as *mut i32,
                &mut sparse_model,
                &mut svm_type,
                &mut kernel_type,
                &mut degree,
                &mut gamma,
                &mut coef0,
                test.as_mut_ptr(),
                &mut xr,
                xrowindex.as_mut_ptr(),
                xcolindex.as_mut_ptr(),
                &mut sparsex,
                ret.as_mut_ptr(),
                dec.as_mut_ptr(),
                prob.as_mut_ptr(),
            );
        }

        let dict = PyDict::new(py);
        dict.set_item("values", ret.into_pyarray(py))?;
        if decision_values {
            dict.set_item("decision_values", dec.into_pyarray(py))?;
        }
        if probability {
            dict.set_item("probabilities", prob.into_pyarray(py))?;
        }
        Ok(dict)
    }

    #[pymodule]
    fn svm(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(train_py, m)?)?;
        m.add_function(wrap_pyfunction!(predict_py, m)?)?;
        m.add_function(wrap_pyfunction!(set_cv_seed_py, m)?)?;
        Ok(())
    }
}
