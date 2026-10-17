//! Allocate and fill a vector, matrix, or array, from matrixStats `src/allocMatrix2.c`.
//!
//! The R wrappers coerce dimensions with `as.integer` or `as.numeric` and then
//! call these routines. The result has the storage mode of `value`: double,
//! integer, or logical. Logical values are R's `0` / `1` / `NA_INTEGER` ints.
//!
//! A zero double, including `-0`, is stored as positive zero. That is the
//! `memset` path: `value == 0` is true for negative zero, and the cleared
//! bytes are `+0`.
//!
//! `allocMatrix2` tests `nr < 0` twice, so a negative `ncol` is not rejected
//! there. R's `allocMatrix` then reports `negative extents to matrix`.
//! `allocArray` multiplies the dimensions in double precision. A negative
//! product is `negative length vectors are not allowed`, and that check is
//! inside `allocVector`, after the scalar check and before the value's type
//! is checked. A non-negative product that still has a missing or negative
//! dimension fails when the `dim` attribute is set, after the type check.
//! Lengths above `2^52` are `vector is too large`. An out-of-range cast of a
//! double length, including `NaN` and `Inf`, is the indefinite `i64` minimum
//! on this platform, which is reported as a negative length.

/// R's integer and logical NA.
const NA_INTEGER: i32 = i32::MIN;

/// `R_XLEN_T_MAX` when long vectors are supported. A length equal to this
/// still attempts allocation. One larger is rejected.
const XLEN_MAX: i64 = 4_503_599_627_370_496;

const TYPE_ERROR: &str = "Argument 'value' must be either of type integer, numeric or logical";
const SCALAR_ERROR: &str = "Argument 'value' must be a scalar";

/// The scalar passed to `fillWithValue`, or the reason that fill will reject it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Scalar {
    /// `REALSXP`. Bits are kept, except `-0`, which becomes `+0`.
    Double(f64),
    /// `INTSXP`. `i32::MIN` is `NA_integer_`.
    Integer(i32),
    /// `LGLSXP`. `1` is TRUE, `0` is FALSE, `i32::MIN` is NA.
    Logical(i32),
    /// Atomic, length 1, but not integer, double, or logical.
    BadType,
    /// Not an atomic vector of length 1.
    NotScalar,
}

impl Scalar {
    pub fn from_parts(kind: &str, real: f64, integer: i32) -> Self {
        match kind {
            "double" => Scalar::Double(real),
            "integer" => Scalar::Integer(integer),
            "logical" => Scalar::Logical(integer),
            "bad" => Scalar::BadType,
            "not_scalar" => Scalar::NotScalar,
            _ => Scalar::BadType,
        }
    }
}

/// A filled block. Logical and integer data share the `i32` payload.
/// Logical NA is [`NA_INTEGER`].
#[derive(Clone, Debug, PartialEq)]
pub enum Allocated {
    Double {
        shape: Vec<usize>,
        values: Vec<f64>,
    },
    Integer {
        shape: Vec<usize>,
        values: Vec<i32>,
    },
}

impl Allocated {
    pub fn shape(&self) -> &[usize] {
        match self {
            Allocated::Double { shape, .. } | Allocated::Integer { shape, .. } => shape,
        }
    }

    pub fn len(&self) -> usize {
        match self {
            Allocated::Double { values, .. } => values.len(),
            Allocated::Integer { values, .. } => values.len(),
        }
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// `allocVector2` after `as.numeric(length)`.
pub fn alloc_vector(length: f64, value: Scalar) -> Result<Allocated, String> {
    let n = cast_xlen(length);
    if n < 0 {
        return Err("Argument 'length' is negative".to_string());
    }
    if matches!(value, Scalar::NotScalar) {
        return Err(SCALAR_ERROR.to_string());
    }
    if n > XLEN_MAX {
        return Err("vector is too large".to_string());
    }
    materialize(vec![n as usize], value)
}

/// `allocMatrix2` after `as.integer` on `nrow` and `ncol`.
pub fn alloc_matrix(nrow: i32, ncol: i32, value: Scalar) -> Result<Allocated, String> {
    if nrow < 0 {
        return Err("Argument 'nrow' is negative".to_string());
    }
    if matches!(value, Scalar::NotScalar) {
        return Err(SCALAR_ERROR.to_string());
    }
    // The C source checks `nr < 0` again and never looks at `nc`.
    if ncol < 0 {
        return Err("negative extents to matrix".to_string());
    }
    let n = cast_xlen(f64::from(nrow) * f64::from(ncol));
    if n > XLEN_MAX {
        return Err("vector is too large".to_string());
    }
    materialize(vec![nrow as usize, ncol as usize], value)
}

/// `allocArray2` after `as.integer(dim)`.
pub fn alloc_array(dim: &[i32], value: Scalar) -> Result<Allocated, String> {
    if dim.is_empty() {
        return Err(
            "Argument 'dim' must be an integer vector of at least length one".to_string(),
        );
    }
    let mut nd = 1.0_f64;
    for &extent in dim {
        nd *= f64::from(extent);
    }
    let n = cast_xlen(nd);
    if matches!(value, Scalar::NotScalar) {
        return Err(SCALAR_ERROR.to_string());
    }
    if n < 0 {
        return Err("negative length vectors are not allowed".to_string());
    }
    if n > XLEN_MAX {
        return Err("vector is too large".to_string());
    }
    if matches!(value, Scalar::BadType) {
        return Err(TYPE_ERROR.to_string());
    }
    if dim.iter().any(|&extent| extent == NA_INTEGER) {
        return Err("the dims contain missing values".to_string());
    }
    if dim.iter().any(|&extent| extent < 0) {
        return Err("the dims contain negative values".to_string());
    }
    let shape = dim.iter().map(|&extent| extent as usize).collect();
    materialize(shape, value)
}

/// Cast the way `cvttsd2si` does on x86_64. Out of range, `NaN`, and
/// infinities become the indefinite integer, `i64::MIN`. In-range values
/// truncate toward zero.
fn cast_xlen(length: f64) -> i64 {
    const LIMIT: f64 = 9223372036854775808.0;
    if !length.is_finite() || length >= LIMIT || length < -LIMIT {
        i64::MIN
    } else {
        length as i64
    }
}

fn materialize(shape: Vec<usize>, value: Scalar) -> Result<Allocated, String> {
    let n = shape.iter().try_fold(1usize, |acc, &extent| acc.checked_mul(extent));
    let Some(n) = n else {
        return Err("vector is too large".to_string());
    };
    match value {
        Scalar::NotScalar => Err(SCALAR_ERROR.to_string()),
        Scalar::BadType => Err(TYPE_ERROR.to_string()),
        Scalar::Double(number) => Ok(Allocated::Double {
            values: fill_f64(n, number),
            shape,
        }),
        Scalar::Integer(number) | Scalar::Logical(number) => Ok(Allocated::Integer {
            values: fill_i32(n, number),
            shape,
        }),
    }
}

fn fill_f64(n: usize, value: f64) -> Vec<f64> {
    // `value == 0` is true for `-0`, and `memset` then stores `+0`.
    if value == 0.0 {
        vec![0.0; n]
    } else {
        vec![value; n]
    }
}

fn fill_i32(n: usize, value: i32) -> Vec<i32> {
    vec![value; n]
}

#[cfg(feature = "python")]
mod py {
    use numpy::ndarray::{ArrayD, IxDyn};
    use numpy::PyArray;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use crate::{alloc_array, alloc_matrix, alloc_vector, Allocated, Scalar};

    fn to_py(py: Python<'_>, allocated: Allocated) -> PyResult<Py<PyAny>> {
        match allocated {
            Allocated::Double { shape, values } => {
                let array = ArrayD::from_shape_vec(IxDyn(&shape), values)
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                Ok(PyArray::from_owned_array(py, array).into_any().unbind())
            }
            Allocated::Integer { shape, values } => {
                let array = ArrayD::from_shape_vec(IxDyn(&shape), values)
                    .map_err(|err| PyValueError::new_err(err.to_string()))?;
                Ok(PyArray::from_owned_array(py, array).into_any().unbind())
            }
        }
    }

    #[pyfunction]
    fn alloc_vector_py(
        py: Python<'_>,
        length: f64,
        kind: &str,
        real: f64,
        integer: i32,
    ) -> PyResult<Py<PyAny>> {
        let value = Scalar::from_parts(kind, real, integer);
        let allocated = py
            .detach(move || alloc_vector(length, value))
            .map_err(PyValueError::new_err)?;
        to_py(py, allocated)
    }

    #[pyfunction]
    fn alloc_matrix_py(
        py: Python<'_>,
        nrow: i32,
        ncol: i32,
        kind: &str,
        real: f64,
        integer: i32,
    ) -> PyResult<Py<PyAny>> {
        let value = Scalar::from_parts(kind, real, integer);
        let allocated = py
            .detach(move || alloc_matrix(nrow, ncol, value))
            .map_err(PyValueError::new_err)?;
        to_py(py, allocated)
    }

    #[pyfunction]
    fn alloc_array_py(
        py: Python<'_>,
        dim: Vec<i32>,
        kind: &str,
        real: f64,
        integer: i32,
    ) -> PyResult<Py<PyAny>> {
        let value = Scalar::from_parts(kind, real, integer);
        let allocated = py
            .detach(move || alloc_array(&dim, value))
            .map_err(PyValueError::new_err)?;
        to_py(py, allocated)
    }

    #[pymodule]
    fn allocmatrix(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(alloc_vector_py, m)?)?;
        m.add_function(wrap_pyfunction!(alloc_matrix_py, m)?)?;
        m.add_function(wrap_pyfunction!(alloc_array_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{alloc_array, alloc_matrix, alloc_vector, Allocated, Scalar, NA_INTEGER};

    fn doubles(result: Allocated) -> (Vec<usize>, Vec<f64>) {
        match result {
            Allocated::Double { shape, values } => (shape, values),
            Allocated::Integer { .. } => panic!("expected double"),
        }
    }

    fn ints(result: Allocated) -> (Vec<usize>, Vec<i32>) {
        match result {
            Allocated::Integer { shape, values } => (shape, values),
            Allocated::Double { .. } => panic!("expected integer"),
        }
    }

    #[test]
    fn matrix_shape_follows_nrow_then_ncol() {
        let (shape, values) = doubles(alloc_matrix(2, 3, Scalar::Double(1.5)).unwrap());
        assert_eq!(shape, vec![2, 3]);
        assert_eq!(values, vec![1.5; 6]);
    }

    #[test]
    fn negative_zero_is_stored_as_positive_zero() {
        let (_, values) = doubles(alloc_vector(3.0, Scalar::Double(-0.0)).unwrap());
        assert!(values.iter().all(|value| value.to_bits() == 0));
    }

    #[test]
    fn negative_ncol_is_the_matrix_extents_error() {
        assert_eq!(
            alloc_matrix(2, -3, Scalar::Double(1.0)).unwrap_err(),
            "negative extents to matrix"
        );
        assert_eq!(
            alloc_matrix(2, NA_INTEGER, Scalar::Integer(1)).unwrap_err(),
            "negative extents to matrix"
        );
        assert_eq!(
            alloc_matrix(-1, -3, Scalar::BadType).unwrap_err(),
            "Argument 'nrow' is negative"
        );
        assert_eq!(
            alloc_matrix(2, -3, Scalar::NotScalar).unwrap_err(),
            "Argument 'value' must be a scalar"
        );
        assert_eq!(
            alloc_matrix(2, -1, Scalar::BadType).unwrap_err(),
            "negative extents to matrix"
        );
    }

    #[test]
    fn length_truncates_toward_zero_and_rejects_a_negative_cast() {
        assert_eq!(
            doubles(alloc_vector(5.9, Scalar::Double(1.0)).unwrap()).1,
            vec![1.0; 5]
        );
        assert!(alloc_vector(-0.1, Scalar::Integer(1)).unwrap().is_empty());
        assert_eq!(
            alloc_vector(-1.9, Scalar::BadType).unwrap_err(),
            "Argument 'length' is negative"
        );
        assert_eq!(
            alloc_vector(f64::NAN, Scalar::NotScalar).unwrap_err(),
            "Argument 'length' is negative"
        );
        assert_eq!(
            alloc_vector(f64::INFINITY, Scalar::Double(1.0)).unwrap_err(),
            "Argument 'length' is negative"
        );
        assert_eq!(
            alloc_vector(1e20, Scalar::Double(0.0)).unwrap_err(),
            "Argument 'length' is negative"
        );
    }

    #[test]
    fn array_error_order_matches_alloc_then_fill_then_dim() {
        assert_eq!(
            alloc_array(&[], Scalar::Double(1.0)).unwrap_err(),
            "Argument 'dim' must be an integer vector of at least length one"
        );
        assert_eq!(
            alloc_array(&[-1], Scalar::NotScalar).unwrap_err(),
            "Argument 'value' must be a scalar"
        );
        assert_eq!(
            alloc_array(&[-1], Scalar::BadType).unwrap_err(),
            "negative length vectors are not allowed"
        );
        assert_eq!(
            alloc_array(&[-2, -3], Scalar::BadType).unwrap_err(),
            "Argument 'value' must be either of type integer, numeric or logical"
        );
        assert_eq!(
            alloc_array(&[-2, -3], Scalar::Double(1.0)).unwrap_err(),
            "the dims contain negative values"
        );
        assert_eq!(
            alloc_array(&[0, NA_INTEGER], Scalar::Integer(1)).unwrap_err(),
            "the dims contain missing values"
        );
        assert_eq!(
            alloc_array(&[-1, -1, -1, -1], Scalar::Logical(1)).unwrap_err(),
            "the dims contain negative values"
        );
        let (shape, values) = ints(alloc_array(&[2, 0, 3], Scalar::Logical(1)).unwrap());
        assert_eq!(shape, vec![2, 0, 3]);
        assert!(values.is_empty());
    }

    #[test]
    fn logical_na_and_integer_na_use_the_same_sentinel() {
        let (_, values) = ints(alloc_vector(2.0, Scalar::Logical(NA_INTEGER)).unwrap());
        assert_eq!(values, vec![NA_INTEGER, NA_INTEGER]);
        let (_, values) = ints(alloc_matrix(1, 2, Scalar::Integer(NA_INTEGER)).unwrap());
        assert_eq!(values, vec![NA_INTEGER, NA_INTEGER]);
    }

    #[test]
    fn lengths_past_the_long_vector_max_are_rejected() {
        assert_eq!(
            alloc_vector(9_007_199_254_740_992.0, Scalar::Double(0.0)).unwrap_err(),
            "vector is too large"
        );
        assert_eq!(
            alloc_matrix(2_147_483_647, 2_147_483_647, Scalar::BadType).unwrap_err(),
            "vector is too large"
        );
        assert_eq!(
            alloc_array(&[2_147_483_647, 2_147_483_647], Scalar::NotScalar).unwrap_err(),
            "Argument 'value' must be a scalar"
        );
    }
}
