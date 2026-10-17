//! Log-sum-exp, ported from matrixStats `src/logSumExp.c`.
//!
//! The public R wrapper always passes `hasNA = TRUE` and `by = 0`. The sum is
//! `max(lx) + log1p(sum(exp(lx - max)))`, skipping one copy of the maximum.
//! An empty selection returns `-Inf`. If every value is missing and `na_rm`
//! is set, the result is `-Inf`; otherwise a missing value is `NaN`.

mod indices;

pub use indices::{
    resolve_f64, resolve_i64, resolve_logical, IndexSpec, IntItem, Logical, MIXED_SIGN,
};

/// R's message when `idxs` is not integer, numeric, or logical.
pub const BAD_IDXS: &str = "idxs can only be integer, numeric, or logical";

/// Accurately compute `log(sum(exp(x)))` over `spec`.
///
/// `na_rm` drops missing values. A missing double is `NaN`, matching R's
/// `NA_real_` in this port.
pub fn log_sum_exp(x: &[f64], spec: &IndexSpec, na_rm: bool) -> f64 {
    match spec {
        IndexSpec::All => scan(x.len(), na_rm, |index| x[index]),
        IndexSpec::At(picked) => scan(picked.len(), na_rm, |index| match picked[index] {
            Some(position) => x[position],
            None => f64::NAN,
        }),
    }
}

fn scan<F>(n: usize, na_rm: bool, mut at: F) -> f64
where
    F: FnMut(usize) -> f64,
{
    if n == 0 {
        return f64::NEG_INFINITY;
    }

    let mut i_max = 0_usize;
    let mut x_max = at(0);
    let mut x_max_is_na = x_max.is_nan();
    if n == 1 {
        if na_rm && x_max_is_na {
            return f64::NEG_INFINITY;
        }
        return x_max;
    }

    let mut saw_na = x_max_is_na;
    for ii in 1..n {
        let xii = at(ii);
        if xii.is_nan() {
            if na_rm {
                saw_na = true;
                continue;
            }
            return f64::NAN;
        }
        if xii > x_max || (na_rm && x_max_is_na) {
            i_max = ii;
            x_max = xii;
            x_max_is_na = x_max.is_nan();
        }
    }

    if x_max_is_na {
        return if na_rm { f64::NEG_INFINITY } else { f64::NAN };
    }
    if x_max == f64::INFINITY {
        return f64::INFINITY;
    }
    if x_max == f64::NEG_INFINITY {
        return f64::NEG_INFINITY;
    }

    let mut sum = 0.0;
    for ii in 0..n {
        if ii == i_max {
            continue;
        }
        let xii = at(ii);
        if !saw_na || !xii.is_nan() {
            sum += (xii - x_max).exp();
        }
    }
    x_max + sum.ln_1p()
}

#[cfg(feature = "python")]
mod py {
    use numpy::{
        dtype, PyArray0, PyArray0Methods, PyArray1, PyArrayDescrMethods, PyArrayMethods,
        PyUntypedArray, PyUntypedArrayMethods,
    };
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList};

    use crate::indices::{resolve_f64, resolve_i64, resolve_logical, IndexSpec, IntItem, Logical};
    use crate::{log_sum_exp, BAD_IDXS};

    #[pyfunction]
    #[pyo3(name = "logSumExp", signature = (lx, idxs=None, na_rm=false))]
    fn log_sum_exp_py(
        py: Python<'_>,
        lx: Bound<'_, PyAny>,
        idxs: Option<Bound<'_, PyAny>>,
        na_rm: bool,
    ) -> PyResult<f64> {
        with_values(py, &lx, |values| {
            let spec = match idxs {
                None => IndexSpec::All,
                Some(idxs) => spec_from_idxs(py, &idxs, values.len())?,
            };
            Ok(log_sum_exp(values, &spec, na_rm))
        })
    }

    fn with_values<T>(
        py: Python<'_>,
        lx: &Bound<'_, PyAny>,
        body: impl FnOnce(&[f64]) -> PyResult<T>,
    ) -> PyResult<T> {
        if let Ok(array) = lx.cast::<PyUntypedArray>() {
            if array.dtype().is_equiv_to(&dtype::<f64>(py)) {
                if array.ndim() == 1 {
                    let typed = array.cast::<PyArray1<f64>>()?;
                    let view = typed.readonly();
                    if let Ok(slice) = view.as_slice() {
                        return body(slice);
                    }
                    let owned: Vec<f64> = view.as_array().iter().copied().collect();
                    return body(&owned);
                }
                if array.ndim() == 0 {
                    let value = [array.cast::<PyArray0<f64>>()?.item()];
                    return body(&value);
                }
            }
        }

        let np = py.import("numpy")?;
        let kwargs = PyDict::new(py);
        kwargs.set_item("dtype", np.getattr("float64")?)?;
        let converted = np.call_method("asarray", (lx,), Some(&kwargs))?;
        let flat = converted.call_method1("ravel", ("F",))?;
        let flat_ndim: usize = flat.getattr("ndim")?.extract()?;
        if flat_ndim == 0 {
            let value = [flat.call_method0("item")?.extract::<f64>()?];
            return body(&value);
        }
        let typed = flat.cast::<PyArray1<f64>>()?;
        let view = typed.readonly();
        if let Ok(slice) = view.as_slice() {
            body(slice)
        } else {
            let owned: Vec<f64> = view.as_array().iter().copied().collect();
            body(&owned)
        }
    }

    fn spec_from_idxs(py: Python<'_>, idxs: &Bound<'_, PyAny>, n: usize) -> PyResult<IndexSpec> {
        let np = py.import("numpy")?;
        let arr = np.getattr("asarray")?.call1((idxs,))?;
        let dtype_obj = arr.getattr("dtype")?;
        let kind: String = dtype_obj.getattr("kind")?.extract()?;
        let itemsize: usize = dtype_obj.getattr("itemsize")?.extract()?;
        let flat = arr.call_method1("ravel", ("F",))?;
        let flat_ndim: usize = flat.getattr("ndim")?.extract()?;
        let items = flat_items(&flat, flat_ndim)?;

        match kind.as_str() {
            "b" => {
                let logical = items
                    .iter()
                    .map(|item| {
                        if item.is_instance_of::<PyBool>() && item.is_truthy()? {
                            Ok(Logical::True)
                        } else if item.is_instance_of::<PyBool>() {
                            Ok(Logical::False)
                        } else {
                            Err(bad_idxs())
                        }
                    })
                    .collect::<PyResult<Vec<_>>>()?;
                Ok(resolve_logical(&logical, n))
            }
            "i" | "u" => {
                let sentinel = if kind == "i" && itemsize == 4 {
                    Some(i32::MIN as i64)
                } else {
                    None
                };
                let ints = items
                    .iter()
                    .map(|item| int_item(item, sentinel))
                    .collect::<PyResult<Vec<_>>>()?;
                resolve_i64(&ints, n).map_err(PyValueError::new_err)
            }
            "f" => {
                let values = items
                    .iter()
                    .map(|item| item.extract::<f64>().map_err(|_| bad_idxs()))
                    .collect::<PyResult<Vec<_>>>()?;
                resolve_f64(&values, n).map_err(PyValueError::new_err)
            }
            "O" => spec_from_objects(&items, n),
            _ => Err(bad_idxs()),
        }
    }

    fn flat_items<'py>(flat: &Bound<'py, PyAny>, ndim: usize) -> PyResult<Vec<Bound<'py, PyAny>>> {
        if ndim == 0 {
            return Ok(vec![flat.call_method0("item")?]);
        }
        let list = flat.call_method0("tolist")?.cast::<PyList>()?.clone();
        Ok(list.iter().collect())
    }

    fn spec_from_objects(items: &[Bound<'_, PyAny>], n: usize) -> PyResult<IndexSpec> {
        let mut saw_bool = false;
        let mut saw_int = false;
        let mut saw_real = false;
        for item in items {
            if item.is_none() {
                continue;
            }
            if item.is_instance_of::<PyBool>() {
                saw_bool = true;
            } else if item.is_instance_of::<PyFloat>() {
                saw_real = true;
            } else if item.is_instance_of::<PyInt>() {
                saw_int = true;
            } else {
                return Err(bad_idxs());
            }
        }

        if saw_real || (saw_bool && saw_int) {
            let values = items
                .iter()
                .map(|item| -> PyResult<f64> {
                    if item.is_none() {
                        Ok(f64::NAN)
                    } else if item.is_instance_of::<PyBool>() {
                        Ok(if item.is_truthy()? { 1.0 } else { 0.0 })
                    } else {
                        item.extract::<f64>().map_err(|_| bad_idxs())
                    }
                })
                .collect::<PyResult<Vec<_>>>()?;
            return resolve_f64(&values, n).map_err(PyValueError::new_err);
        }
        if saw_int {
            let ints = items
                .iter()
                .map(|item| {
                    if item.is_none() {
                        Ok(IntItem::Missing)
                    } else {
                        int_item(item, None)
                    }
                })
                .collect::<PyResult<Vec<_>>>()?;
            return resolve_i64(&ints, n).map_err(PyValueError::new_err);
        }
        let logical = items
            .iter()
            .map(|item| -> PyResult<Logical> {
                if item.is_none() {
                    Ok(Logical::Na)
                } else if item.is_instance_of::<PyBool>() {
                    Ok(if item.is_truthy()? {
                        Logical::True
                    } else {
                        Logical::False
                    })
                } else {
                    Err(bad_idxs())
                }
            })
            .collect::<PyResult<Vec<_>>>()?;
        Ok(resolve_logical(&logical, n))
    }

    fn int_item(item: &Bound<'_, PyAny>, sentinel: Option<i64>) -> PyResult<IntItem> {
        if item.is_none() {
            return Ok(IntItem::Missing);
        }
        if let Ok(value) = item.extract::<i64>() {
            if sentinel == Some(value) {
                return Ok(IntItem::Missing);
            }
            return Ok(IntItem::Value(value));
        }
        let positive = item.gt(0)?;
        if positive {
            Ok(IntItem::Value(i64::MAX))
        } else {
            Ok(IntItem::Value(i64::MIN))
        }
    }

    fn bad_idxs() -> PyErr {
        PyValueError::new_err(BAD_IDXS)
    }

    #[pymodule]
    fn logsumexp(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(log_sum_exp_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn close(actual: f64, expected: f64) -> bool {
        if expected.is_nan() {
            actual.is_nan()
        } else {
            actual == expected || (actual - expected).abs() < 1e-8
        }
    }

    #[test]
    fn subtracts_the_maximum_before_the_exponential() {
        let y = log_sum_exp(&[1000.01, 1000.02], &IndexSpec::All, false);
        assert!(close(y, 1000.7081596805078));
        let y = log_sum_exp(&[-1000.01, -1000.02], &IndexSpec::All, false);
        assert!(close(y, -999.32184031949214));
    }

    #[test]
    fn empty_and_missing_inputs() {
        assert_eq!(log_sum_exp(&[], &IndexSpec::All, false), f64::NEG_INFINITY);
        assert_eq!(
            log_sum_exp(&[f64::NAN], &IndexSpec::All, true),
            f64::NEG_INFINITY
        );
        assert!(log_sum_exp(&[f64::NAN], &IndexSpec::All, false).is_nan());
        assert_eq!(
            log_sum_exp(&[f64::NAN, f64::NAN], &IndexSpec::All, true),
            f64::NEG_INFINITY
        );
        assert!(log_sum_exp(&[f64::NAN, f64::NAN], &IndexSpec::All, false).is_nan());
        assert_eq!(log_sum_exp(&[1.0], &IndexSpec::All, false), 1.0);
    }

    #[test]
    fn infinities_and_a_leading_missing_value() {
        assert_eq!(
            log_sum_exp(&[1.0, 2.0, f64::INFINITY], &IndexSpec::All, false),
            f64::INFINITY
        );
        assert_eq!(
            log_sum_exp(
                &[f64::NEG_INFINITY, f64::NEG_INFINITY],
                &IndexSpec::All,
                false
            ),
            f64::NEG_INFINITY
        );
        assert_eq!(
            log_sum_exp(
                &[f64::NEG_INFINITY, 5.0, f64::NEG_INFINITY],
                &IndexSpec::All,
                false
            ),
            5.0
        );
        assert!(log_sum_exp(&[f64::NAN, 1.0], &IndexSpec::All, false).is_nan());
        assert_eq!(log_sum_exp(&[f64::NAN, 1.0], &IndexSpec::All, true), 1.0);
        assert!(close(
            log_sum_exp(&[1.0, f64::NAN, 3.0], &IndexSpec::All, true),
            3.1269280110429727
        ));
    }

    #[test]
    fn duplicate_maxima_contribute_one() {
        assert!(close(
            log_sum_exp(&[2.0, 2.0], &IndexSpec::All, false),
            2.6931471805599454
        ));
        assert!(close(
            log_sum_exp(&[1.0, 2.0, 2.0], &IndexSpec::All, false),
            2.8619948040582512
        ));
    }

    #[test]
    fn indexed_values_match_the_subset() {
        let x = [5.0, 6.0, 7.0];
        let spec = resolve_i64(
            &[
                IntItem::Value(0),
                IntItem::Value(2),
                IntItem::Value(0),
                IntItem::Value(2),
            ],
            x.len(),
        )
        .unwrap();
        assert!(close(log_sum_exp(&x, &spec, false), 6.6931471805599454));

        let spec = resolve_f64(&[0.5], 3).unwrap();
        assert_eq!(log_sum_exp(&[9.0, 8.0, 7.0], &spec, false), 9.0);
    }
}
