//! `between` from data.table `src/between.c`, and exact rolling windows from `src/froll.c`.
//!
//! An integer is missing when it equals R's `NA_INTEGER`. A double is missing
//! when it is NaN, which covers R's real NA. A string is missing when it is
//! `None`. Empty input on any side is an empty logical vector. Each side must
//! be length 1 or the length of the longest side.

mod froll;
mod idate;

const NA_INTEGER: i32 = i32::MIN;

fn lengths(nx: usize, nl: usize, nu: usize) -> Result<usize, String> {
    if nx == 0 || nl == 0 || nu == 0 {
        return Ok(0);
    }
    let longest = nx.max(nl).max(nu);
    if (nl != 1 && nl != longest) || (nu != 1 && nu != longest) || (nx != 1 && nx != longest) {
        return Err(format!(
            "Incompatible vector lengths: length(x)=={nx} length(lower)=={nl} length(upper)=={nu}. Each should be either length 1 or the length of the longest."
        ));
    }
    Ok(longest)
}

fn index(i: usize, n: usize) -> usize {
    if n == 1 { 0 } else { i }
}

/// Closed bounds use `open == false`. `NA` bounds count as infinite when
/// `na_bounds` is true, matching `NAbounds=TRUE`.
pub fn between_i32(
    x: &[i32],
    lower: &[i32],
    upper: &[i32],
    open: bool,
    na_bounds: bool,
    check: bool,
) -> Result<Vec<i8>, String> {
    let longest = lengths(x.len(), lower.len(), upper.len())?;
    if longest == 0 {
        return Ok(Vec::new());
    }
    let step = if open { 1i64 } else { 0 };
    if check {
        let bound = lower.len().max(upper.len());
        for i in 0..bound {
            let l = lower[index(i, lower.len())];
            let u = upper[index(i, upper.len())];
            if l != NA_INTEGER && u != NA_INTEGER && l > u {
                return Err(format!(
                    "Item {} of lower ({l}) is greater than item {} of upper ({u})",
                    index(i, lower.len()) + 1,
                    index(i, upper.len()) + 1
                ));
            }
        }
    }
    let mut ans = vec![0i8; longest];
    for i in 0..longest {
        let elem = x[index(i, x.len())];
        let l = lower[index(i, lower.len())];
        let u = upper[index(i, upper.len())];
        ans[i] = logical_i32(elem, l, u, step, na_bounds);
    }
    Ok(ans)
}

fn logical_i32(elem: i32, l: i32, u: i32, step: i64, na_bounds: bool) -> i8 {
    if elem == NA_INTEGER {
        return -1;
    }
    let elem = elem as i64;
    let below = |bound: i32| elem < bound as i64 + step;
    let above = |bound: i32| elem > bound as i64 - step;
    let inside = |bound_low: i32, bound_up: i32| !below(bound_low) && !above(bound_up);
    if na_bounds {
        let lok = l == NA_INTEGER || !below(l);
        let uok = u == NA_INTEGER || !above(u);
        if lok && uok { 1 } else { 0 }
    } else {
        let lok = l != NA_INTEGER;
        let uok = u != NA_INTEGER;
        if lok && uok {
            if inside(l, u) { 1 } else { 0 }
        } else if (uok && above(u)) || (lok && below(l)) {
            0
        } else {
            -1
        }
    }
}

pub fn between_f64(
    x: &[f64],
    lower: &[f64],
    upper: &[f64],
    open: bool,
    na_bounds: bool,
    check: bool,
) -> Result<Vec<i8>, String> {
    let longest = lengths(x.len(), lower.len(), upper.len())?;
    if longest == 0 {
        return Ok(Vec::new());
    }
    if check {
        let bound = lower.len().max(upper.len());
        for i in 0..bound {
            let l = lower[index(i, lower.len())];
            let u = upper[index(i, upper.len())];
            if !l.is_nan() && !u.is_nan() && l > u {
                return Err(format!(
                    "Item {} of lower ({l:.6}) is greater than item {} of upper ({u:.6})",
                    index(i, lower.len()) + 1,
                    index(i, upper.len()) + 1
                ));
            }
        }
    }
    let mut ans = vec![0i8; longest];
    for i in 0..longest {
        let elem = x[index(i, x.len())];
        let l = lower[index(i, lower.len())];
        let u = upper[index(i, upper.len())];
        ans[i] = logical_f64(elem, l, u, open, na_bounds);
    }
    Ok(ans)
}

fn logical_f64(elem: f64, l: f64, u: f64, open: bool, na_bounds: bool) -> i8 {
    if elem.is_nan() {
        return -1;
    }
    let below = |bound: f64| if open { elem <= bound } else { elem < bound };
    let above = |bound: f64| if open { elem >= bound } else { elem > bound };
    if na_bounds {
        let lok = l.is_nan() || !below(l);
        let uok = u.is_nan() || !above(u);
        if lok && uok { 1 } else { 0 }
    } else {
        let lok = !l.is_nan();
        let uok = !u.is_nan();
        if lok && uok {
            if !below(l) && !above(u) { 1 } else { 0 }
        } else if (uok && above(u)) || (lok && below(l)) {
            0
        } else {
            -1
        }
    }
}

pub fn between_str(
    x: &[Option<&str>],
    lower: &[Option<&str>],
    upper: &[Option<&str>],
    open: bool,
    na_bounds: bool,
    check: bool,
) -> Result<Vec<i8>, String> {
    let longest = lengths(x.len(), lower.len(), upper.len())?;
    if longest == 0 {
        return Ok(Vec::new());
    }
    if check {
        let bound = lower.len().max(upper.len());
        for i in 0..bound {
            let l = lower[index(i, lower.len())];
            let u = upper[index(i, upper.len())];
            if let (Some(ls), Some(us)) = (l, u) {
                if ls > us {
                    return Err(format!(
                        "Item {} of lower ('{ls}') is greater than item {} of upper ('{us}')",
                        index(i, lower.len()) + 1,
                        index(i, upper.len()) + 1
                    ));
                }
            }
        }
    }
    let mut ans = vec![0i8; longest];
    for i in 0..longest {
        ans[i] = logical_str(
            x[index(i, x.len())],
            lower[index(i, lower.len())],
            upper[index(i, upper.len())],
            open,
            na_bounds,
        );
    }
    Ok(ans)
}

fn logical_str(
    elem: Option<&str>,
    l: Option<&str>,
    u: Option<&str>,
    open: bool,
    na_bounds: bool,
) -> i8 {
    let Some(elem) = elem else { return -1 };
    let below = |bound: &str| if open { elem <= bound } else { elem < bound };
    let above = |bound: &str| if open { elem >= bound } else { elem > bound };
    if na_bounds {
        let lok = l.map(|bound| !below(bound)).unwrap_or(true);
        let uok = u.map(|bound| !above(bound)).unwrap_or(true);
        if lok && uok { 1 } else { 0 }
    } else {
        match (l, u) {
            (Some(l), Some(u)) => {
                if !below(l) && !above(u) { 1 } else { 0 }
            }
            (l, u) => {
                let too_high = u.map(|bound| above(bound)).unwrap_or(false);
                let too_low = l.map(|bound| below(bound)).unwrap_or(false);
                if too_high || too_low { 0 } else { -1 }
            }
        }
    }
}

#[cfg(feature = "python")]
mod py {
    use pyo3::exceptions::PyRuntimeError;
    use pyo3::prelude::*;

    use crate::froll::{parse_roll, roll_right};
    use crate::idate::{convert_dates, parse_part};
    use crate::{between_f64, between_i32, between_str};

    fn fail(err: String) -> PyErr {
        PyRuntimeError::new_err(err)
    }

    #[pyfunction]
    fn between_i32_py(
        x: Vec<i32>,
        lower: Vec<i32>,
        upper: Vec<i32>,
        open: bool,
        na_bounds: bool,
        check: bool,
    ) -> PyResult<Vec<i8>> {
        between_i32(&x, &lower, &upper, open, na_bounds, check).map_err(fail)
    }

    #[pyfunction]
    fn between_f64_py(
        x: Vec<f64>,
        lower: Vec<f64>,
        upper: Vec<f64>,
        open: bool,
        na_bounds: bool,
        check: bool,
    ) -> PyResult<Vec<i8>> {
        between_f64(&x, &lower, &upper, open, na_bounds, check).map_err(fail)
    }

    #[pyfunction]
    fn between_str_py(
        x: Vec<Option<String>>,
        lower: Vec<Option<String>>,
        upper: Vec<Option<String>>,
        open: bool,
        na_bounds: bool,
        check: bool,
    ) -> PyResult<Vec<i8>> {
        let x_ref: Vec<Option<&str>> = x.iter().map(|item| item.as_deref()).collect();
        let lower_ref: Vec<Option<&str>> = lower.iter().map(|item| item.as_deref()).collect();
        let upper_ref: Vec<Option<&str>> = upper.iter().map(|item| item.as_deref()).collect();
        between_str(&x_ref, &lower_ref, &upper_ref, open, na_bounds, check).map_err(fail)
    }

    #[pyfunction]
    fn convert_date_py(days: Vec<i32>, part: String) -> PyResult<Vec<f64>> {
        let kind = parse_part(&part).ok_or_else(|| fail(format!("unknown date part '{part}'")))?;
        Ok(convert_dates(&days, kind))
    }

    #[pyfunction]
    fn froll_right_py(kind: String, x: Vec<f64>, k: usize, fill: f64, na_rm: bool) -> PyResult<Vec<f64>> {
        let fun = parse_roll(&kind).ok_or_else(|| fail(format!("unknown rolling function '{kind}'")))?;
        Ok(roll_right(&x, k, fill, na_rm, fun))
    }

    #[pymodule]
    fn datatable_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(between_i32_py, m)?)?;
        m.add_function(wrap_pyfunction!(between_f64_py, m)?)?;
        m.add_function(wrap_pyfunction!(between_str_py, m)?)?;
        m.add_function(wrap_pyfunction!(froll_right_py, m)?)?;
        m.add_function(wrap_pyfunction!(convert_date_py, m)?)?;
        Ok(())
    }
}
