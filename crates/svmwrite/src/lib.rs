//! Export a fitted e1071 SVM to libsvm text format (`Rsvm.c` ``svmwrite``).

#[link(name = "e1071_svmwrite", kind = "static")]
#[link(name = "svm_kernel", kind = "static")]
#[link(name = "stdc++")]
extern "C" {
    fn e1071_svmwrite(
        v: *mut f64,
        r: *mut i32,
        c: *mut i32,
        rowindex: *mut i32,
        colindex: *mut i32,
        coefs: *mut f64,
        rho: *mut f64,
        compprob: *mut i32,
        prob_a: *mut f64,
        prob_b: *mut f64,
        nclasses: *mut i32,
        tot_nsv: *mut i32,
        labels: *mut i32,
        nsv: *mut i32,
        sparsemodel: *mut i32,
        svm_type: *mut i32,
        kernel_type: *mut i32,
        degree: *mut i32,
        gamma: *mut f64,
        coef0: *mut f64,
        filename: *const i8,
    );
}

#[cfg(feature = "python")]
mod py {
    use numpy::PyReadonlyArray1;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use std::ffi::CString;

    use crate::e1071_svmwrite;

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
    #[pyo3(name = "write_model", signature = (
        sv,
        coefs,
        rho,
        *,
        tot_nsv,
        sv_nc,
        nclasses,
        labels,
        nsv,
        svm_type=0,
        kernel_type=2,
        degree=3,
        gamma=0.1,
        coef0=0.0,
        compprob=false,
        prob_a=None,
        prob_b=None,
        sparse_model=false,
        rowindex=None,
        colindex=None,
        filename,
    ))]
    fn write_model_py(
        _py: Python<'_>,
        sv: PyReadonlyArray1<'py, f64>,
        coefs: PyReadonlyArray1<'py, f64>,
        rho: PyReadonlyArray1<'py, f64>,
        mut tot_nsv: i32,
        sv_nc: i32,
        nclasses: i32,
        labels: PyReadonlyArray1<'py, i32>,
        nsv: PyReadonlyArray1<'py, i32>,
        svm_type: i32,
        kernel_type: i32,
        degree: i32,
        gamma: f64,
        coef0: f64,
        compprob: bool,
        prob_a: Option<PyReadonlyArray1<'py, f64>>,
        prob_b: Option<PyReadonlyArray1<'py, f64>>,
        sparse_model: bool,
        rowindex: Option<PyReadonlyArray1<'py, i32>>,
        colindex: Option<PyReadonlyArray1<'py, i32>>,
        filename: &str,
    ) -> PyResult<()> {
        let mut v = owned_f64(&sv)?;
        let coefs = owned_f64(&coefs)?;
        let mut rho = owned_f64(&rho)?;
        let labels = owned_i32(&labels)?;
        let nsv = owned_i32(&nsv)?;

        let mut r = tot_nsv;
        let mut c = sv_nc;
        if !sparse_model {
            if r <= 0 || c <= 0 {
                return Err(PyValueError::new_err("tot_nsv and sv_nc must be positive"));
            }
            if v.len() != r as usize * c as usize {
                return Err(PyValueError::new_err("sv length must be tot_nsv * sv_nc"));
            }
        }

        let (mut rowindex_vec, mut colindex_vec) = match (rowindex, colindex) {
            (Some(ri), Some(ci)) => (owned_i32(&ri)?, owned_i32(&ci)?),
            (None, None) if !sparse_model => (vec![0i32], vec![0i32]),
            _ => {
                return Err(PyValueError::new_err(
                    "rowindex and colindex must both be set for sparse models",
                ));
            }
        };

        let mut proba = prob_a.map(|a| owned_f64(&a)).transpose()?.unwrap_or_default();
        let mut probb = prob_b.map(|b| owned_f64(&b)).transpose()?.unwrap_or_default();

        let mut compprob_i = i32::from(compprob);
        let mut sparse_flag = i32::from(sparse_model);
        let mut nclasses = nclasses;
        let mut svm_type = svm_type;
        let mut kernel_type = kernel_type;
        let mut degree = degree;
        let mut gamma = gamma;
        let mut coef0 = coef0;

        let path = CString::new(filename).map_err(|_| PyValueError::new_err("filename contains NUL"))?;

        unsafe {
            e1071_svmwrite(
                v.as_mut_ptr(),
                &mut r,
                &mut c,
                rowindex_vec.as_mut_ptr(),
                colindex_vec.as_mut_ptr(),
                coefs.as_ptr() as *mut f64,
                rho.as_mut_ptr(),
                &mut compprob_i,
                proba.as_mut_ptr(),
                probb.as_mut_ptr(),
                &mut nclasses,
                &mut tot_nsv,
                labels.as_ptr() as *mut i32,
                nsv.as_ptr() as *mut i32,
                &mut sparse_flag,
                &mut svm_type,
                &mut kernel_type,
                &mut degree,
                &mut gamma,
                &mut coef0,
                path.as_ptr(),
            );
        }
        Ok(())
    }

    #[pymodule]
    fn svmwrite(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(write_model_py, m)?)?;
        Ok(())
    }
}
