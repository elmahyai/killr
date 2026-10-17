use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple};

fn arity(args: &Bound<'_, PyTuple>, n: usize, name: &str) -> PyResult<()> {
    if args.len() == n {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!(
            "{name} expects {n} arguments, got {}",
            args.len()
        )))
    }
}

#[pyfunction]
#[pyo3(name = "es1e")]
fn es1e_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "es1e")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut sigsq: f64 = args.get_item(2)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(3)?.extract()?;
    let mut n: i32 = args.get_item(4)?.extract()?;
    let mut g: i32 = args.get_item(5)?.extract()?;
    let mut vinv: f64 = args.get_item(6)?.extract()?;
    let mut hood: f64 = args.get_item(7)?.extract()?;
    let mut z: Vec<f64> = args.get_item(8)?.extract()?;
    crate::es1e(&mut x, &mut mu, &mut sigsq, &mut pro, &mut n, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "hc1e")]
fn hc1e_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 7, "hc1e")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut ic: Vec<i32> = args.get_item(2)?.extract()?;
    let mut ng: i32 = args.get_item(3)?.extract()?;
    let mut ns: i32 = args.get_item(4)?.extract()?;
    let mut nd: i32 = args.get_item(5)?.extract()?;
    let mut d: Vec<f64> = args.get_item(6)?.extract()?;
    crate::hc1e(&mut x, &mut n, &mut ic, &mut ng, &mut ns, &mut nd, &mut d);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(ic)?;
    out.append(ng)?;
    out.append(ns)?;
    out.append(nd)?;
    out.append(d)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "me1e")]
fn me1e_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "me1e")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut vinv: f64 = args.get_item(4)?.extract()?;
    let mut z: Vec<f64> = args.get_item(5)?.extract()?;
    let mut maxi: i32 = args.get_item(6)?.extract()?;
    let mut tol: f64 = args.get_item(7)?.extract()?;
    let mut eps: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut sigsq: f64 = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    crate::me1e(&mut eqpro, &mut x, &mut n, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "me1ep")]
fn me1ep_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 16, "me1ep")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut vinv: f64 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: f64 = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut z: Vec<f64> = args.get_item(9)?.extract()?;
    let mut maxi: i32 = args.get_item(10)?.extract()?;
    let mut tol: f64 = args.get_item(11)?.extract()?;
    let mut eps: f64 = args.get_item(12)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(13)?.extract()?;
    let mut sigsq: f64 = args.get_item(14)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(15)?.extract()?;
    crate::me1ep(&mut eqpro, &mut x, &mut n, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "ms1e")]
fn ms1e_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 7, "ms1e")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(4)?.extract()?;
    let mut sigsq: f64 = args.get_item(5)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(6)?.extract()?;
    crate::ms1e(&mut x, &mut z, &mut n, &mut g, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "ms1ep")]
fn ms1ep_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "ms1ep")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut pshrnk: f64 = args.get_item(4)?.extract()?;
    let mut pmu: f64 = args.get_item(5)?.extract()?;
    let mut pscale: f64 = args.get_item(6)?.extract()?;
    let mut pdof: f64 = args.get_item(7)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(8)?.extract()?;
    let mut sigsq: f64 = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    crate::ms1ep(&mut x, &mut z, &mut n, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "eseee")]
fn eseee_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "eseee")?;
    let mut chol: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(2)?.extract()?;
    let mut sigma: Vec<f64> = args.get_item(3)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(4)?.extract()?;
    let mut n: i32 = args.get_item(5)?.extract()?;
    let mut p: i32 = args.get_item(6)?.extract()?;
    let mut g: i32 = args.get_item(7)?.extract()?;
    let mut vinv: f64 = args.get_item(8)?.extract()?;
    let mut w: Vec<f64> = args.get_item(9)?.extract()?;
    let mut hood: f64 = args.get_item(10)?.extract()?;
    let mut z: Vec<f64> = args.get_item(11)?.extract()?;
    crate::eseee(&mut chol, &mut x, &mut mu, &mut sigma, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut w, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(chol)?;
    out.append(x)?;
    out.append(mu)?;
    out.append(sigma)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(w)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeee")]
fn meeee_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "meeee")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut u: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    let mut w: Vec<f64> = args.get_item(13)?.extract()?;
    crate::meeee(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut u, &mut pro, &mut w);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    out.append(w)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeeep")]
fn meeeep_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "meeeep")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut u: Vec<f64> = args.get_item(15)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(16)?.extract()?;
    let mut w: Vec<f64> = args.get_item(17)?.extract()?;
    crate::meeeep(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut u, &mut pro, &mut w);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    out.append(w)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseee")]
fn mseee_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "mseee")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut w: Vec<f64> = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut u: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(8)?.extract()?;
    crate::mseee(&mut x, &mut z, &mut n, &mut p, &mut g, &mut w, &mut mu, &mut u, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(w)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseeep")]
fn mseeep_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 13, "mseeep")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut w: Vec<f64> = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut u: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    crate::mseeep(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut w, &mut mu, &mut u, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(w)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "eseei")]
fn eseei_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "eseei")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut scale: f64 = args.get_item(2)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(3)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(4)?.extract()?;
    let mut n: i32 = args.get_item(5)?.extract()?;
    let mut p: i32 = args.get_item(6)?.extract()?;
    let mut g: i32 = args.get_item(7)?.extract()?;
    let mut vinv: f64 = args.get_item(8)?.extract()?;
    let mut hood: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    crate::eseei(&mut x, &mut mu, &mut scale, &mut shape, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeei")]
fn meeei_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "meeei")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut scale: f64 = args.get_item(11)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(12)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(13)?.extract()?;
    crate::meeei(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeeip")]
fn meeeip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "meeeip")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: f64 = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut scale: f64 = args.get_item(15)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(16)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(17)?.extract()?;
    crate::meeeip(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseei")]
fn mseei_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "mseei")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut scale: f64 = args.get_item(6)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(8)?.extract()?;
    crate::mseei(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseeip")]
fn mseeip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 13, "mseeip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut scale: f64 = args.get_item(10)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    crate::mseeip(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "eseev")]
fn eseev_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "eseev")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut scale: f64 = args.get_item(2)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(3)?.extract()?;
    let mut o: Vec<f64> = args.get_item(4)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(5)?.extract()?;
    let mut n: i32 = args.get_item(6)?.extract()?;
    let mut p: i32 = args.get_item(7)?.extract()?;
    let mut g: i32 = args.get_item(8)?.extract()?;
    let mut vinv: f64 = args.get_item(9)?.extract()?;
    let mut v: Vec<f64> = args.get_item(10)?.extract()?;
    let mut w: Vec<f64> = args.get_item(11)?.extract()?;
    let mut hood: f64 = args.get_item(12)?.extract()?;
    let mut z: Vec<f64> = args.get_item(13)?.extract()?;
    crate::eseev(&mut x, &mut mu, &mut scale, &mut shape, &mut o, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut v, &mut w, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(v)?;
    out.append(w)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeev")]
fn meeev_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "meeev")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut lwork: i32 = args.get_item(10)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(11)?.extract()?;
    let mut scale: f64 = args.get_item(12)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(13)?.extract()?;
    let mut o: Vec<f64> = args.get_item(14)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(15)?.extract()?;
    let mut w: Vec<f64> = args.get_item(16)?.extract()?;
    let mut s: Vec<f64> = args.get_item(17)?.extract()?;
    crate::meeev(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut lwork, &mut mu, &mut scale, &mut shape, &mut o, &mut pro, &mut w, &mut s);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(lwork)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    out.append(w)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeevp")]
fn meeevp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 22, "meeevp")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut lwork: i32 = args.get_item(14)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(15)?.extract()?;
    let mut scale: f64 = args.get_item(16)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(17)?.extract()?;
    let mut o: Vec<f64> = args.get_item(18)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(19)?.extract()?;
    let mut w: Vec<f64> = args.get_item(20)?.extract()?;
    let mut s: Vec<f64> = args.get_item(21)?.extract()?;
    crate::meeevp(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut lwork, &mut mu, &mut scale, &mut shape, &mut o, &mut pro, &mut w, &mut s);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(lwork)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    out.append(w)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseev")]
fn mseev_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "mseev")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut w: Vec<f64> = args.get_item(5)?.extract()?;
    let mut lwork: i32 = args.get_item(6)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: f64 = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut o: Vec<f64> = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    crate::mseev(&mut x, &mut z, &mut n, &mut p, &mut g, &mut w, &mut lwork, &mut mu, &mut scale, &mut shape, &mut o, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(w)?;
    out.append(lwork)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseevp")]
fn mseevp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 16, "mseevp")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut w: Vec<f64> = args.get_item(9)?.extract()?;
    let mut lwork: i32 = args.get_item(10)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(11)?.extract()?;
    let mut scale: f64 = args.get_item(12)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(13)?.extract()?;
    let mut o: Vec<f64> = args.get_item(14)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(15)?.extract()?;
    crate::mseevp(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut w, &mut lwork, &mut mu, &mut scale, &mut shape, &mut o, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(w)?;
    out.append(lwork)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "eseii")]
fn eseii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 10, "eseii")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut sigsq: f64 = args.get_item(2)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(3)?.extract()?;
    let mut n: i32 = args.get_item(4)?.extract()?;
    let mut p: i32 = args.get_item(5)?.extract()?;
    let mut g: i32 = args.get_item(6)?.extract()?;
    let mut vinv: f64 = args.get_item(7)?.extract()?;
    let mut hood: f64 = args.get_item(8)?.extract()?;
    let mut z: Vec<f64> = args.get_item(9)?.extract()?;
    crate::eseii(&mut x, &mut mu, &mut sigsq, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "hceii")]
fn hceii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "hceii")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut ic: Vec<i32> = args.get_item(3)?.extract()?;
    let mut ng: i32 = args.get_item(4)?.extract()?;
    let mut ns: i32 = args.get_item(5)?.extract()?;
    let mut v: Vec<f64> = args.get_item(6)?.extract()?;
    let mut nd: i32 = args.get_item(7)?.extract()?;
    let mut d: Vec<f64> = args.get_item(8)?.extract()?;
    crate::hceii(&mut x, &mut n, &mut p, &mut ic, &mut ng, &mut ns, &mut v, &mut nd, &mut d);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(ic)?;
    out.append(ng)?;
    out.append(ns)?;
    out.append(v)?;
    out.append(nd)?;
    out.append(d)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeii")]
fn meeii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 13, "meeii")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut sigsq: f64 = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    crate::meeii(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeiip")]
fn meeiip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 17, "meeiip")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: f64 = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut sigsq: f64 = args.get_item(15)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(16)?.extract()?;
    crate::meeiip(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseii")]
fn mseii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 8, "mseii")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut sigsq: f64 = args.get_item(6)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(7)?.extract()?;
    crate::mseii(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseiip")]
fn mseiip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "mseiip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut sigsq: f64 = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    crate::mseiip(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esevi")]
fn esevi_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "esevi")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut scale: f64 = args.get_item(2)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(3)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(4)?.extract()?;
    let mut n: i32 = args.get_item(5)?.extract()?;
    let mut p: i32 = args.get_item(6)?.extract()?;
    let mut g: i32 = args.get_item(7)?.extract()?;
    let mut vinv: f64 = args.get_item(8)?.extract()?;
    let mut hood: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    crate::esevi(&mut x, &mut mu, &mut scale, &mut shape, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meevi")]
fn meevi_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "meevi")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut scale: f64 = args.get_item(11)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(12)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(13)?.extract()?;
    crate::meevi(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meevip")]
fn meevip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "meevip")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: f64 = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut scale: f64 = args.get_item(15)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(16)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(17)?.extract()?;
    crate::meevip(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msevi")]
fn msevi_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "msevi")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut scale: f64 = args.get_item(6)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(8)?.extract()?;
    crate::msevi(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msevip")]
fn msevip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 13, "msevip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut scale: f64 = args.get_item(10)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    crate::msevip(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "es1v")]
fn es1v_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "es1v")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(2)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(3)?.extract()?;
    let mut n: i32 = args.get_item(4)?.extract()?;
    let mut g: i32 = args.get_item(5)?.extract()?;
    let mut vinv: f64 = args.get_item(6)?.extract()?;
    let mut hood: f64 = args.get_item(7)?.extract()?;
    let mut z: Vec<f64> = args.get_item(8)?.extract()?;
    crate::es1v(&mut x, &mut mu, &mut sigsq, &mut pro, &mut n, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "hc1v")]
fn hc1v_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 8, "hc1v")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut ic: Vec<i32> = args.get_item(2)?.extract()?;
    let mut ng: i32 = args.get_item(3)?.extract()?;
    let mut ns: i32 = args.get_item(4)?.extract()?;
    let mut alpha: f64 = args.get_item(5)?.extract()?;
    let mut nd: i32 = args.get_item(6)?.extract()?;
    let mut d: Vec<f64> = args.get_item(7)?.extract()?;
    crate::hc1v(&mut x, &mut n, &mut ic, &mut ng, &mut ns, &mut alpha, &mut nd, &mut d);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(ic)?;
    out.append(ng)?;
    out.append(ns)?;
    out.append(alpha)?;
    out.append(nd)?;
    out.append(d)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "me1v")]
fn me1v_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "me1v")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut vinv: f64 = args.get_item(4)?.extract()?;
    let mut z: Vec<f64> = args.get_item(5)?.extract()?;
    let mut maxi: i32 = args.get_item(6)?.extract()?;
    let mut tol: f64 = args.get_item(7)?.extract()?;
    let mut eps: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    crate::me1v(&mut eqpro, &mut x, &mut n, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "me1vp")]
fn me1vp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 16, "me1vp")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut vinv: f64 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: f64 = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut z: Vec<f64> = args.get_item(9)?.extract()?;
    let mut maxi: i32 = args.get_item(10)?.extract()?;
    let mut tol: f64 = args.get_item(11)?.extract()?;
    let mut eps: f64 = args.get_item(12)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(13)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(14)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(15)?.extract()?;
    crate::me1vp(&mut eqpro, &mut x, &mut n, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "ms1v")]
fn ms1v_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 7, "ms1v")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(4)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(5)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(6)?.extract()?;
    crate::ms1v(&mut x, &mut z, &mut n, &mut g, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "ms1vp")]
fn ms1vp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "ms1vp")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut pshrnk: f64 = args.get_item(4)?.extract()?;
    let mut pmu: f64 = args.get_item(5)?.extract()?;
    let mut pscale: f64 = args.get_item(6)?.extract()?;
    let mut pdof: f64 = args.get_item(7)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(8)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    crate::ms1vp(&mut x, &mut z, &mut n, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esvei")]
fn esvei_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "esvei")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(2)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(3)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(4)?.extract()?;
    let mut n: i32 = args.get_item(5)?.extract()?;
    let mut p: i32 = args.get_item(6)?.extract()?;
    let mut g: i32 = args.get_item(7)?.extract()?;
    let mut vinv: f64 = args.get_item(8)?.extract()?;
    let mut hood: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    crate::esvei(&mut x, &mut mu, &mut scale, &mut shape, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevei")]
fn mevei_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 17, "mevei")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: Vec<i32> = args.get_item(7)?.extract()?;
    let mut tol: Vec<f64> = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(11)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(12)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(13)?.extract()?;
    let mut scl: Vec<f64> = args.get_item(14)?.extract()?;
    let mut shp: Vec<f64> = args.get_item(15)?.extract()?;
    let mut w: Vec<f64> = args.get_item(16)?.extract()?;
    crate::mevei(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro, &mut scl, &mut shp, &mut w);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(scl)?;
    out.append(shp)?;
    out.append(w)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meveip")]
fn meveip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 21, "meveip")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: f64 = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: Vec<i32> = args.get_item(11)?.extract()?;
    let mut tol: Vec<f64> = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(15)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(16)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(17)?.extract()?;
    let mut scl: Vec<f64> = args.get_item(18)?.extract()?;
    let mut shp: Vec<f64> = args.get_item(19)?.extract()?;
    let mut w: Vec<f64> = args.get_item(20)?.extract()?;
    crate::meveip(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro, &mut scl, &mut shp, &mut w);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(scl)?;
    out.append(shp)?;
    out.append(w)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvei")]
fn msvei_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "msvei")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut maxi: i32 = args.get_item(5)?.extract()?;
    let mut tol: f64 = args.get_item(6)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut scl: Vec<f64> = args.get_item(11)?.extract()?;
    let mut shp: Vec<f64> = args.get_item(12)?.extract()?;
    let mut w: Vec<f64> = args.get_item(13)?.extract()?;
    crate::msvei(&mut x, &mut z, &mut n, &mut p, &mut g, &mut maxi, &mut tol, &mut mu, &mut scale, &mut shape, &mut pro, &mut scl, &mut shp, &mut w);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(scl)?;
    out.append(shp)?;
    out.append(w)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msveip")]
fn msveip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "msveip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut maxi: i32 = args.get_item(9)?.extract()?;
    let mut tol: f64 = args.get_item(10)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(11)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(12)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(13)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(14)?.extract()?;
    let mut scl: Vec<f64> = args.get_item(15)?.extract()?;
    let mut shp: Vec<f64> = args.get_item(16)?.extract()?;
    let mut w: Vec<f64> = args.get_item(17)?.extract()?;
    crate::msveip(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut maxi, &mut tol, &mut mu, &mut scale, &mut shape, &mut pro, &mut scl, &mut shp, &mut w);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(scl)?;
    out.append(shp)?;
    out.append(w)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esvev")]
fn esvev_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "esvev")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(2)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(3)?.extract()?;
    let mut o: Vec<f64> = args.get_item(4)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(5)?.extract()?;
    let mut n: i32 = args.get_item(6)?.extract()?;
    let mut p: i32 = args.get_item(7)?.extract()?;
    let mut g: i32 = args.get_item(8)?.extract()?;
    let mut vinv: f64 = args.get_item(9)?.extract()?;
    let mut v: Vec<f64> = args.get_item(10)?.extract()?;
    let mut w: Vec<f64> = args.get_item(11)?.extract()?;
    let mut hood: f64 = args.get_item(12)?.extract()?;
    let mut z: Vec<f64> = args.get_item(13)?.extract()?;
    crate::esvev(&mut x, &mut mu, &mut scale, &mut shape, &mut o, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut v, &mut w, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(v)?;
    out.append(w)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevev")]
fn mevev_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "mevev")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: Vec<i32> = args.get_item(7)?.extract()?;
    let mut tol: Vec<f64> = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut lwork: i32 = args.get_item(10)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(11)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(12)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(13)?.extract()?;
    let mut o: Vec<f64> = args.get_item(14)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(15)?.extract()?;
    let mut w: Vec<f64> = args.get_item(16)?.extract()?;
    let mut s: Vec<f64> = args.get_item(17)?.extract()?;
    crate::mevev(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut lwork, &mut mu, &mut scale, &mut shape, &mut o, &mut pro, &mut w, &mut s);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(lwork)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    out.append(w)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevevp")]
fn mevevp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 22, "mevevp")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: Vec<i32> = args.get_item(11)?.extract()?;
    let mut tol: Vec<f64> = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut lwork: i32 = args.get_item(14)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(15)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(16)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(17)?.extract()?;
    let mut o: Vec<f64> = args.get_item(18)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(19)?.extract()?;
    let mut w: Vec<f64> = args.get_item(20)?.extract()?;
    let mut s: Vec<f64> = args.get_item(21)?.extract()?;
    crate::mevevp(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut lwork, &mut mu, &mut scale, &mut shape, &mut o, &mut pro, &mut w, &mut s);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(lwork)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    out.append(w)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvev")]
fn msvev_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "msvev")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut w: Vec<f64> = args.get_item(5)?.extract()?;
    let mut lwork: i32 = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(10)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(11)?.extract()?;
    let mut o: Vec<f64> = args.get_item(12)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(13)?.extract()?;
    crate::msvev(&mut x, &mut z, &mut n, &mut p, &mut g, &mut w, &mut lwork, &mut maxi, &mut tol, &mut mu, &mut scale, &mut shape, &mut o, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(w)?;
    out.append(lwork)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvevp")]
fn msvevp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "msvevp")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut w: Vec<f64> = args.get_item(9)?.extract()?;
    let mut lwork: i32 = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(13)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(14)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(15)?.extract()?;
    let mut o: Vec<f64> = args.get_item(16)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(17)?.extract()?;
    crate::msvevp(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut w, &mut lwork, &mut maxi, &mut tol, &mut mu, &mut scale, &mut shape, &mut o, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(w)?;
    out.append(lwork)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(o)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esvii")]
fn esvii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 10, "esvii")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(2)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(3)?.extract()?;
    let mut n: i32 = args.get_item(4)?.extract()?;
    let mut p: i32 = args.get_item(5)?.extract()?;
    let mut g: i32 = args.get_item(6)?.extract()?;
    let mut vinv: f64 = args.get_item(7)?.extract()?;
    let mut hood: f64 = args.get_item(8)?.extract()?;
    let mut z: Vec<f64> = args.get_item(9)?.extract()?;
    crate::esvii(&mut x, &mut mu, &mut sigsq, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "hcvii")]
fn hcvii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 10, "hcvii")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut ic: Vec<i32> = args.get_item(3)?.extract()?;
    let mut ng: i32 = args.get_item(4)?.extract()?;
    let mut ns: i32 = args.get_item(5)?.extract()?;
    let mut alpha: f64 = args.get_item(6)?.extract()?;
    let mut v: Vec<f64> = args.get_item(7)?.extract()?;
    let mut nd: i32 = args.get_item(8)?.extract()?;
    let mut d: Vec<f64> = args.get_item(9)?.extract()?;
    crate::hcvii(&mut x, &mut n, &mut p, &mut ic, &mut ng, &mut ns, &mut alpha, &mut v, &mut nd, &mut d);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(ic)?;
    out.append(ng)?;
    out.append(ns)?;
    out.append(alpha)?;
    out.append(v)?;
    out.append(nd)?;
    out.append(d)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevii")]
fn mevii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 13, "mevii")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    crate::mevii(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meviip")]
fn meviip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 17, "meviip")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: f64 = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(15)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(16)?.extract()?;
    crate::meviip(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvii")]
fn msvii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 8, "msvii")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(7)?.extract()?;
    crate::msvii(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msviip")]
fn msviip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "msviip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut sigsq: Vec<f64> = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    crate::msviip(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut sigsq, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esvvi")]
fn esvvi_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "esvvi")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(2)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(3)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(4)?.extract()?;
    let mut n: i32 = args.get_item(5)?.extract()?;
    let mut p: i32 = args.get_item(6)?.extract()?;
    let mut g: i32 = args.get_item(7)?.extract()?;
    let mut vinv: f64 = args.get_item(8)?.extract()?;
    let mut hood: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    crate::esvvi(&mut x, &mut mu, &mut scale, &mut shape, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevvi")]
fn mevvi_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "mevvi")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(11)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(12)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(13)?.extract()?;
    crate::mevvi(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevvip")]
fn mevvip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "mevvip")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: f64 = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(15)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(16)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(17)?.extract()?;
    crate::mevvip(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvvi")]
fn msvvi_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "msvvi")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(6)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(8)?.extract()?;
    crate::msvvi(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvvip")]
fn msvvip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 13, "msvvip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: f64 = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(10)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    crate::msvvip(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut scale, &mut shape, &mut pro);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esvvv")]
fn esvvv_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "esvvv")?;
    let mut chol: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(2)?.extract()?;
    let mut sigma: Vec<f64> = args.get_item(3)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(4)?.extract()?;
    let mut n: i32 = args.get_item(5)?.extract()?;
    let mut p: i32 = args.get_item(6)?.extract()?;
    let mut g: i32 = args.get_item(7)?.extract()?;
    let mut vinv: f64 = args.get_item(8)?.extract()?;
    let mut w: Vec<f64> = args.get_item(9)?.extract()?;
    let mut hood: f64 = args.get_item(10)?.extract()?;
    let mut z: Vec<f64> = args.get_item(11)?.extract()?;
    crate::esvvv(&mut chol, &mut x, &mut mu, &mut sigma, &mut pro, &mut n, &mut p, &mut g, &mut vinv, &mut w, &mut hood, &mut z);
    let out = PyList::empty(py);
    out.append(chol)?;
    out.append(x)?;
    out.append(mu)?;
    out.append(sigma)?;
    out.append(pro)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(w)?;
    out.append(hood)?;
    out.append(z)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mcltrw")]
fn mcltrw_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 5, "mcltrw")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut u: Vec<f64> = args.get_item(3)?.extract()?;
    let mut ss: f64 = args.get_item(4)?.extract()?;
    crate::mcltrw(&mut x, &mut n, &mut p, &mut u, &mut ss);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(u)?;
    out.append(ss)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "hcvvv")]
fn hcvvv_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "hcvvv")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut ic: Vec<i32> = args.get_item(3)?.extract()?;
    let mut ng: i32 = args.get_item(4)?.extract()?;
    let mut ns: i32 = args.get_item(5)?.extract()?;
    let mut alpha: f64 = args.get_item(6)?.extract()?;
    let mut beta: f64 = args.get_item(7)?.extract()?;
    let mut v: Vec<f64> = args.get_item(8)?.extract()?;
    let mut u: Vec<f64> = args.get_item(9)?.extract()?;
    let mut s: Vec<f64> = args.get_item(10)?.extract()?;
    let mut r: Vec<f64> = args.get_item(11)?.extract()?;
    let mut nd: i32 = args.get_item(12)?.extract()?;
    let mut d: Vec<f64> = args.get_item(13)?.extract()?;
    crate::hcvvv(&mut x, &mut n, &mut p, &mut ic, &mut ng, &mut ns, &mut alpha, &mut beta, &mut v, &mut u, &mut s, &mut r, &mut nd, &mut d);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(ic)?;
    out.append(ng)?;
    out.append(ns)?;
    out.append(alpha)?;
    out.append(beta)?;
    out.append(v)?;
    out.append(u)?;
    out.append(s)?;
    out.append(r)?;
    out.append(nd)?;
    out.append(d)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevvv")]
fn mevvv_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 15, "mevvv")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut z: Vec<f64> = args.get_item(6)?.extract()?;
    let mut maxi: i32 = args.get_item(7)?.extract()?;
    let mut tol: f64 = args.get_item(8)?.extract()?;
    let mut eps: f64 = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut u: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    let mut w: Vec<f64> = args.get_item(13)?.extract()?;
    let mut s: Vec<f64> = args.get_item(14)?.extract()?;
    crate::mevvv(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut u, &mut pro, &mut w, &mut s);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    out.append(w)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevvvp")]
fn mevvvp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 19, "mevvvp")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut vinv: f64 = args.get_item(5)?.extract()?;
    let mut pshrnk: f64 = args.get_item(6)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut pdof: f64 = args.get_item(9)?.extract()?;
    let mut z: Vec<f64> = args.get_item(10)?.extract()?;
    let mut maxi: i32 = args.get_item(11)?.extract()?;
    let mut tol: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(14)?.extract()?;
    let mut u: Vec<f64> = args.get_item(15)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(16)?.extract()?;
    let mut w: Vec<f64> = args.get_item(17)?.extract()?;
    let mut s: Vec<f64> = args.get_item(18)?.extract()?;
    crate::mevvvp(&mut eqpro, &mut x, &mut n, &mut p, &mut g, &mut vinv, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut u, &mut pro, &mut w, &mut s);
    let out = PyList::empty(py);
    out.append(eqpro)?;
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(vinv)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(z)?;
    out.append(maxi)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    out.append(w)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvvv")]
fn msvvv_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 10, "msvvv")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut w: Vec<f64> = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut u: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(8)?.extract()?;
    let mut s: Vec<f64> = args.get_item(9)?.extract()?;
    crate::msvvv(&mut x, &mut z, &mut n, &mut p, &mut g, &mut w, &mut mu, &mut u, &mut pro, &mut s);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(w)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvvvp")]
fn msvvvp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "msvvvp")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut pshrnk: f64 = args.get_item(5)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(7)?.extract()?;
    let mut pdof: f64 = args.get_item(8)?.extract()?;
    let mut w: Vec<f64> = args.get_item(9)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(10)?.extract()?;
    let mut u: Vec<f64> = args.get_item(11)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(12)?.extract()?;
    let mut s: Vec<f64> = args.get_item(13)?.extract()?;
    crate::msvvvp(&mut x, &mut z, &mut n, &mut p, &mut g, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut w, &mut mu, &mut u, &mut pro, &mut s);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(w)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(pro)?;
    out.append(s)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mvn1d")]
fn mvn1d_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 5, "mvn1d")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut mu: f64 = args.get_item(2)?.extract()?;
    let mut sigsq: f64 = args.get_item(3)?.extract()?;
    let mut hood: f64 = args.get_item(4)?.extract()?;
    crate::mvn1d(&mut x, &mut n, &mut mu, &mut sigsq, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mvn1p")]
fn mvn1p_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 9, "mvn1p")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut pshrnk: f64 = args.get_item(2)?.extract()?;
    let mut pmu: f64 = args.get_item(3)?.extract()?;
    let mut pscale: f64 = args.get_item(4)?.extract()?;
    let mut pdof: f64 = args.get_item(5)?.extract()?;
    let mut mu: f64 = args.get_item(6)?.extract()?;
    let mut sigsq: f64 = args.get_item(7)?.extract()?;
    let mut hood: f64 = args.get_item(8)?.extract()?;
    crate::mvn1p(&mut x, &mut n, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut sigsq, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mnxiip")]
fn mnxiip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 10, "mnxiip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut pshrnk: f64 = args.get_item(3)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(4)?.extract()?;
    let mut pscale: f64 = args.get_item(5)?.extract()?;
    let mut pdof: f64 = args.get_item(6)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut sigsq: f64 = args.get_item(8)?.extract()?;
    let mut hood: f64 = args.get_item(9)?.extract()?;
    crate::mnxiip(&mut x, &mut n, &mut p, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut sigsq, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mvnxii")]
fn mvnxii_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 6, "mvnxii")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(3)?.extract()?;
    let mut sigsq: f64 = args.get_item(4)?.extract()?;
    let mut hood: f64 = args.get_item(5)?.extract()?;
    crate::mvnxii(&mut x, &mut n, &mut p, &mut mu, &mut sigsq, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(mu)?;
    out.append(sigsq)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mnxxip")]
fn mnxxip_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "mnxxip")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut pshrnk: f64 = args.get_item(3)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(4)?.extract()?;
    let mut pscale: f64 = args.get_item(5)?.extract()?;
    let mut pdof: f64 = args.get_item(6)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: f64 = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut hood: f64 = args.get_item(10)?.extract()?;
    crate::mnxxip(&mut x, &mut n, &mut p, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut scale, &mut shape, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mvnxxi")]
fn mvnxxi_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 7, "mvnxxi")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(3)?.extract()?;
    let mut scale: f64 = args.get_item(4)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(5)?.extract()?;
    let mut hood: f64 = args.get_item(6)?.extract()?;
    crate::mvnxxi(&mut x, &mut n, &mut p, &mut mu, &mut scale, &mut shape, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(mu)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mnxxxp")]
fn mnxxxp_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 11, "mnxxxp")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut w: Vec<f64> = args.get_item(3)?.extract()?;
    let mut pshrnk: f64 = args.get_item(4)?.extract()?;
    let mut pmu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut pscale: Vec<f64> = args.get_item(6)?.extract()?;
    let mut pdof: f64 = args.get_item(7)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(8)?.extract()?;
    let mut u: Vec<f64> = args.get_item(9)?.extract()?;
    let mut hood: f64 = args.get_item(10)?.extract()?;
    crate::mnxxxp(&mut x, &mut n, &mut p, &mut w, &mut pshrnk, &mut pmu, &mut pscale, &mut pdof, &mut mu, &mut u, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(w)?;
    out.append(pshrnk)?;
    out.append(pmu)?;
    out.append(pscale)?;
    out.append(pdof)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mvnxxx")]
fn mvnxxx_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 6, "mvnxxx")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(3)?.extract()?;
    let mut u: Vec<f64> = args.get_item(4)?.extract()?;
    let mut hood: f64 = args.get_item(5)?.extract()?;
    crate::mvnxxx(&mut x, &mut n, &mut p, &mut mu, &mut u, &mut hood);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(hood)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "hceee")]
fn hceee_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 12, "hceee")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut n: i32 = args.get_item(1)?.extract()?;
    let mut p: i32 = args.get_item(2)?.extract()?;
    let mut ic: Vec<i32> = args.get_item(3)?.extract()?;
    let mut ng: i32 = args.get_item(4)?.extract()?;
    let mut ns: i32 = args.get_item(5)?.extract()?;
    let mut io: Vec<i32> = args.get_item(6)?.extract()?;
    let mut jo: Vec<i32> = args.get_item(7)?.extract()?;
    let mut v: Vec<f64> = args.get_item(8)?.extract()?;
    let mut s: Vec<f64> = args.get_item(9)?.extract()?;
    let mut u: Vec<f64> = args.get_item(10)?.extract()?;
    let mut r: Vec<f64> = args.get_item(11)?.extract()?;
    crate::hceee(&mut x, &mut n, &mut p, &mut ic, &mut ng, &mut ns, &mut io, &mut jo, &mut v, &mut s, &mut u, &mut r);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(n)?;
    out.append(p)?;
    out.append(ic)?;
    out.append(ng)?;
    out.append(ns)?;
    out.append(io)?;
    out.append(jo)?;
    out.append(v)?;
    out.append(s)?;
    out.append(u)?;
    out.append(r)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msevv")]
fn msevv_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "msevv")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut o: Vec<f64> = args.get_item(6)?.extract()?;
    let mut u: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut lwork: i32 = args.get_item(11)?.extract()?;
    let mut info: i32 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    crate::msevv(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut o, &mut u, &mut scale, &mut shape, &mut pro, &mut lwork, &mut info, &mut eps);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(u)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(lwork)?;
    out.append(info)?;
    out.append(eps)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esevv")]
fn esevv_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "esevv")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: f64 = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut vinv: f64 = args.get_item(11)?.extract()?;
    let mut loglik: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    crate::esevv(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut o, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eps);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eps)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meevv")]
fn meevv_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 22, "meevv")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut u: Vec<f64> = args.get_item(8)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(9)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    let mut vinv: f64 = args.get_item(12)?.extract()?;
    let mut loglik: f64 = args.get_item(13)?.extract()?;
    let mut eqpro: i32 = args.get_item(14)?.extract()?;
    let mut itmax: i32 = args.get_item(15)?.extract()?;
    let mut tol: f64 = args.get_item(16)?.extract()?;
    let mut eps: f64 = args.get_item(17)?.extract()?;
    let mut niterout: i32 = args.get_item(18)?.extract()?;
    let mut errout: f64 = args.get_item(19)?.extract()?;
    let mut lwork: i32 = args.get_item(20)?.extract()?;
    let mut info: i32 = args.get_item(21)?.extract()?;
    crate::meevv(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut o, &mut u, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eqpro, &mut itmax, &mut tol, &mut eps, &mut niterout, &mut errout, &mut lwork, &mut info);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(u)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eqpro)?;
    out.append(itmax)?;
    out.append(tol)?;
    out.append(eps)?;
    out.append(niterout)?;
    out.append(errout)?;
    out.append(lwork)?;
    out.append(info)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvee")]
fn msvee_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 16, "msvee")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut u: Vec<f64> = args.get_item(6)?.extract()?;
    let mut c: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(9)?.extract()?;
    let mut lwork: i32 = args.get_item(10)?.extract()?;
    let mut info: i32 = args.get_item(11)?.extract()?;
    let mut itmax: i32 = args.get_item(12)?.extract()?;
    let mut tol: f64 = args.get_item(13)?.extract()?;
    let mut niterin: i32 = args.get_item(14)?.extract()?;
    let mut errin: f64 = args.get_item(15)?.extract()?;
    crate::msvee(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut u, &mut c, &mut scale, &mut pro, &mut lwork, &mut info, &mut itmax, &mut tol, &mut niterin, &mut errin);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(c)?;
    out.append(scale)?;
    out.append(pro)?;
    out.append(lwork)?;
    out.append(info)?;
    out.append(itmax)?;
    out.append(tol)?;
    out.append(niterin)?;
    out.append(errin)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esvee")]
fn esvee_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "esvee")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut vinv: f64 = args.get_item(11)?.extract()?;
    let mut loglik: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    crate::esvee(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut o, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eps);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eps)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevee")]
fn mevee_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 26, "mevee")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut c: Vec<f64> = args.get_item(7)?.extract()?;
    let mut u: Vec<f64> = args.get_item(8)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(9)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    let mut vinv: f64 = args.get_item(12)?.extract()?;
    let mut loglik: f64 = args.get_item(13)?.extract()?;
    let mut eqpro: i32 = args.get_item(14)?.extract()?;
    let mut itmaxin: i32 = args.get_item(15)?.extract()?;
    let mut tolin: f64 = args.get_item(16)?.extract()?;
    let mut itmaxout: i32 = args.get_item(17)?.extract()?;
    let mut tolout: f64 = args.get_item(18)?.extract()?;
    let mut eps: f64 = args.get_item(19)?.extract()?;
    let mut niterin: i32 = args.get_item(20)?.extract()?;
    let mut errin: f64 = args.get_item(21)?.extract()?;
    let mut niterout: i32 = args.get_item(22)?.extract()?;
    let mut errout: f64 = args.get_item(23)?.extract()?;
    let mut lwork: i32 = args.get_item(24)?.extract()?;
    let mut info: i32 = args.get_item(25)?.extract()?;
    crate::mevee(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut c, &mut u, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eqpro, &mut itmaxin, &mut tolin, &mut itmaxout, &mut tolout, &mut eps, &mut niterin, &mut errin, &mut niterout, &mut errout, &mut lwork, &mut info);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(c)?;
    out.append(u)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eqpro)?;
    out.append(itmaxin)?;
    out.append(tolin)?;
    out.append(itmaxout)?;
    out.append(tolout)?;
    out.append(eps)?;
    out.append(niterin)?;
    out.append(errin)?;
    out.append(niterout)?;
    out.append(errout)?;
    out.append(lwork)?;
    out.append(info)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mseve")]
fn mseve_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "mseve")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut u: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: f64 = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut lwork: i32 = args.get_item(11)?.extract()?;
    let mut info: i32 = args.get_item(12)?.extract()?;
    let mut itmax: i32 = args.get_item(13)?.extract()?;
    let mut tol: f64 = args.get_item(14)?.extract()?;
    let mut niterin: i32 = args.get_item(15)?.extract()?;
    let mut errin: f64 = args.get_item(16)?.extract()?;
    let mut eps: f64 = args.get_item(17)?.extract()?;
    crate::mseve(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut u, &mut o, &mut scale, &mut shape, &mut pro, &mut lwork, &mut info, &mut itmax, &mut tol, &mut niterin, &mut errin, &mut eps);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(o)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(lwork)?;
    out.append(info)?;
    out.append(itmax)?;
    out.append(tol)?;
    out.append(niterin)?;
    out.append(errin)?;
    out.append(eps)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "eseve")]
fn eseve_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "eseve")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: f64 = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut vinv: f64 = args.get_item(11)?.extract()?;
    let mut loglik: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    crate::eseve(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut o, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eps);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eps)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "meeve")]
fn meeve_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 26, "meeve")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut u: Vec<f64> = args.get_item(8)?.extract()?;
    let mut scale: f64 = args.get_item(9)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    let mut vinv: f64 = args.get_item(12)?.extract()?;
    let mut loglik: f64 = args.get_item(13)?.extract()?;
    let mut eqpro: i32 = args.get_item(14)?.extract()?;
    let mut itmaxin: i32 = args.get_item(15)?.extract()?;
    let mut tolin: f64 = args.get_item(16)?.extract()?;
    let mut itmaxout: i32 = args.get_item(17)?.extract()?;
    let mut tolout: f64 = args.get_item(18)?.extract()?;
    let mut eps: f64 = args.get_item(19)?.extract()?;
    let mut niterin: i32 = args.get_item(20)?.extract()?;
    let mut errin: f64 = args.get_item(21)?.extract()?;
    let mut niterout: i32 = args.get_item(22)?.extract()?;
    let mut errout: f64 = args.get_item(23)?.extract()?;
    let mut lwork: i32 = args.get_item(24)?.extract()?;
    let mut info: i32 = args.get_item(25)?.extract()?;
    crate::meeve(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut o, &mut u, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eqpro, &mut itmaxin, &mut tolin, &mut itmaxout, &mut tolout, &mut eps, &mut niterin, &mut errin, &mut niterout, &mut errout, &mut lwork, &mut info);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(u)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eqpro)?;
    out.append(itmaxin)?;
    out.append(tolin)?;
    out.append(itmaxout)?;
    out.append(tolout)?;
    out.append(eps)?;
    out.append(niterin)?;
    out.append(errin)?;
    out.append(niterout)?;
    out.append(errout)?;
    out.append(lwork)?;
    out.append(info)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "msvve")]
fn msvve_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 18, "msvve")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(5)?.extract()?;
    let mut u: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut lwork: i32 = args.get_item(11)?.extract()?;
    let mut info: i32 = args.get_item(12)?.extract()?;
    let mut itmax: i32 = args.get_item(13)?.extract()?;
    let mut tol: f64 = args.get_item(14)?.extract()?;
    let mut niterin: i32 = args.get_item(15)?.extract()?;
    let mut errin: f64 = args.get_item(16)?.extract()?;
    let mut eps: f64 = args.get_item(17)?.extract()?;
    crate::msvve(&mut x, &mut z, &mut n, &mut p, &mut g, &mut mu, &mut u, &mut o, &mut scale, &mut shape, &mut pro, &mut lwork, &mut info, &mut itmax, &mut tol, &mut niterin, &mut errin, &mut eps);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(mu)?;
    out.append(u)?;
    out.append(o)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(lwork)?;
    out.append(info)?;
    out.append(itmax)?;
    out.append(tol)?;
    out.append(niterin)?;
    out.append(errin)?;
    out.append(eps)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "esvve")]
fn esvve_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 14, "esvve")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(8)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(9)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(10)?.extract()?;
    let mut vinv: f64 = args.get_item(11)?.extract()?;
    let mut loglik: f64 = args.get_item(12)?.extract()?;
    let mut eps: f64 = args.get_item(13)?.extract()?;
    crate::esvve(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut o, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eps);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eps)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "mevve")]
fn mevve_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 26, "mevve")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut z: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut p: i32 = args.get_item(3)?.extract()?;
    let mut g: i32 = args.get_item(4)?.extract()?;
    let mut gnoise: i32 = args.get_item(5)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(6)?.extract()?;
    let mut o: Vec<f64> = args.get_item(7)?.extract()?;
    let mut u: Vec<f64> = args.get_item(8)?.extract()?;
    let mut scale: Vec<f64> = args.get_item(9)?.extract()?;
    let mut shape: Vec<f64> = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    let mut vinv: f64 = args.get_item(12)?.extract()?;
    let mut loglik: f64 = args.get_item(13)?.extract()?;
    let mut eqpro: i32 = args.get_item(14)?.extract()?;
    let mut itmaxin: i32 = args.get_item(15)?.extract()?;
    let mut tolin: f64 = args.get_item(16)?.extract()?;
    let mut itmaxout: i32 = args.get_item(17)?.extract()?;
    let mut tolout: f64 = args.get_item(18)?.extract()?;
    let mut eps: f64 = args.get_item(19)?.extract()?;
    let mut niterin: i32 = args.get_item(20)?.extract()?;
    let mut errin: f64 = args.get_item(21)?.extract()?;
    let mut niterout: i32 = args.get_item(22)?.extract()?;
    let mut errout: f64 = args.get_item(23)?.extract()?;
    let mut lwork: i32 = args.get_item(24)?.extract()?;
    let mut info: i32 = args.get_item(25)?.extract()?;
    crate::mevve(&mut x, &mut z, &mut n, &mut p, &mut g, &mut gnoise, &mut mu, &mut o, &mut u, &mut scale, &mut shape, &mut pro, &mut vinv, &mut loglik, &mut eqpro, &mut itmaxin, &mut tolin, &mut itmaxout, &mut tolout, &mut eps, &mut niterin, &mut errin, &mut niterout, &mut errout, &mut lwork, &mut info);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(z)?;
    out.append(n)?;
    out.append(p)?;
    out.append(g)?;
    out.append(gnoise)?;
    out.append(mu)?;
    out.append(o)?;
    out.append(u)?;
    out.append(scale)?;
    out.append(shape)?;
    out.append(pro)?;
    out.append(vinv)?;
    out.append(loglik)?;
    out.append(eqpro)?;
    out.append(itmaxin)?;
    out.append(tolin)?;
    out.append(itmaxout)?;
    out.append(tolout)?;
    out.append(eps)?;
    out.append(niterin)?;
    out.append(errin)?;
    out.append(niterout)?;
    out.append(errout)?;
    out.append(lwork)?;
    out.append(info)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "dmvnorm")]
fn dmvnorm_py<'py>(py: Python<'py>, args: Bound<'py, PyTuple>) -> PyResult<Bound<'py, PyList>> {
    arity(&args, 8, "dmvnorm")?;
    let mut x: Vec<f64> = args.get_item(0)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(1)?.extract()?;
    let mut sigma: Vec<f64> = args.get_item(2)?.extract()?;
    let mut n: i32 = args.get_item(3)?.extract()?;
    let mut p: i32 = args.get_item(4)?.extract()?;
    let mut w: Vec<f64> = args.get_item(5)?.extract()?;
    let mut hood: f64 = args.get_item(6)?.extract()?;
    let mut logdens: Vec<f64> = args.get_item(7)?.extract()?;
    crate::dmvnorm(&mut x, &mut mu, &mut sigma, &mut n, &mut p, &mut w, &mut hood, &mut logdens);
    let out = PyList::empty(py);
    out.append(x)?;
    out.append(mu)?;
    out.append(sigma)?;
    out.append(n)?;
    out.append(p)?;
    out.append(w)?;
    out.append(hood)?;
    out.append(logdens)?;
    Ok(out)
}

#[pyfunction]
#[pyo3(name = "me1e_ms")]
fn me1e_ms_py(args: Bound<'_, PyTuple>) -> PyResult<f64> {
    arity(&args, 12, "me1e_ms")?;
    let mut eqpro: i32 = args.get_item(0)?.extract()?;
    let mut x: Vec<f64> = args.get_item(1)?.extract()?;
    let mut n: i32 = args.get_item(2)?.extract()?;
    let mut g: i32 = args.get_item(3)?.extract()?;
    let mut vinv: f64 = args.get_item(4)?.extract()?;
    let mut z: Vec<f64> = args.get_item(5)?.extract()?;
    let mut maxi: i32 = args.get_item(6)?.extract()?;
    let mut tol: f64 = args.get_item(7)?.extract()?;
    let mut eps: f64 = args.get_item(8)?.extract()?;
    let mut mu: Vec<f64> = args.get_item(9)?.extract()?;
    let mut sigsq: f64 = args.get_item(10)?.extract()?;
    let mut pro: Vec<f64> = args.get_item(11)?.extract()?;
    Ok(crate::me1e_ms(&mut eqpro, &mut x, &mut n, &mut g, &mut vinv, &mut z, &mut maxi, &mut tol, &mut eps, &mut mu, &mut sigsq, &mut pro))
}

#[pymodule]
fn mclust_kernels(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(es1e_py, m)?)?;
    m.add_function(wrap_pyfunction!(hc1e_py, m)?)?;
    m.add_function(wrap_pyfunction!(me1e_py, m)?)?;
    m.add_function(wrap_pyfunction!(me1ep_py, m)?)?;
    m.add_function(wrap_pyfunction!(ms1e_py, m)?)?;
    m.add_function(wrap_pyfunction!(ms1ep_py, m)?)?;
    m.add_function(wrap_pyfunction!(eseee_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeee_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeeep_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseee_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseeep_py, m)?)?;
    m.add_function(wrap_pyfunction!(eseei_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeei_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeeip_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseei_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseeip_py, m)?)?;
    m.add_function(wrap_pyfunction!(eseev_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeev_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeevp_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseev_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseevp_py, m)?)?;
    m.add_function(wrap_pyfunction!(eseii_py, m)?)?;
    m.add_function(wrap_pyfunction!(hceii_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeii_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeiip_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseii_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseiip_py, m)?)?;
    m.add_function(wrap_pyfunction!(esevi_py, m)?)?;
    m.add_function(wrap_pyfunction!(meevi_py, m)?)?;
    m.add_function(wrap_pyfunction!(meevip_py, m)?)?;
    m.add_function(wrap_pyfunction!(msevi_py, m)?)?;
    m.add_function(wrap_pyfunction!(msevip_py, m)?)?;
    m.add_function(wrap_pyfunction!(es1v_py, m)?)?;
    m.add_function(wrap_pyfunction!(hc1v_py, m)?)?;
    m.add_function(wrap_pyfunction!(me1v_py, m)?)?;
    m.add_function(wrap_pyfunction!(me1vp_py, m)?)?;
    m.add_function(wrap_pyfunction!(ms1v_py, m)?)?;
    m.add_function(wrap_pyfunction!(ms1vp_py, m)?)?;
    m.add_function(wrap_pyfunction!(esvei_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevei_py, m)?)?;
    m.add_function(wrap_pyfunction!(meveip_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvei_py, m)?)?;
    m.add_function(wrap_pyfunction!(msveip_py, m)?)?;
    m.add_function(wrap_pyfunction!(esvev_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevev_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevevp_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvev_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvevp_py, m)?)?;
    m.add_function(wrap_pyfunction!(esvii_py, m)?)?;
    m.add_function(wrap_pyfunction!(hcvii_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevii_py, m)?)?;
    m.add_function(wrap_pyfunction!(meviip_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvii_py, m)?)?;
    m.add_function(wrap_pyfunction!(msviip_py, m)?)?;
    m.add_function(wrap_pyfunction!(esvvi_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevvi_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevvip_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvvi_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvvip_py, m)?)?;
    m.add_function(wrap_pyfunction!(esvvv_py, m)?)?;
    m.add_function(wrap_pyfunction!(hcvvv_py, m)?)?;
    m.add_function(wrap_pyfunction!(mcltrw_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevvv_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevvvp_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvvv_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvvvp_py, m)?)?;
    m.add_function(wrap_pyfunction!(mvn1d_py, m)?)?;
    m.add_function(wrap_pyfunction!(mvn1p_py, m)?)?;
    m.add_function(wrap_pyfunction!(mnxiip_py, m)?)?;
    m.add_function(wrap_pyfunction!(mvnxii_py, m)?)?;
    m.add_function(wrap_pyfunction!(mnxxip_py, m)?)?;
    m.add_function(wrap_pyfunction!(mvnxxi_py, m)?)?;
    m.add_function(wrap_pyfunction!(mnxxxp_py, m)?)?;
    m.add_function(wrap_pyfunction!(mvnxxx_py, m)?)?;
    m.add_function(wrap_pyfunction!(hceee_py, m)?)?;
    m.add_function(wrap_pyfunction!(msevv_py, m)?)?;
    m.add_function(wrap_pyfunction!(esevv_py, m)?)?;
    m.add_function(wrap_pyfunction!(meevv_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvee_py, m)?)?;
    m.add_function(wrap_pyfunction!(esvee_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevee_py, m)?)?;
    m.add_function(wrap_pyfunction!(mseve_py, m)?)?;
    m.add_function(wrap_pyfunction!(eseve_py, m)?)?;
    m.add_function(wrap_pyfunction!(meeve_py, m)?)?;
    m.add_function(wrap_pyfunction!(msvve_py, m)?)?;
    m.add_function(wrap_pyfunction!(esvve_py, m)?)?;
    m.add_function(wrap_pyfunction!(mevve_py, m)?)?;
    m.add_function(wrap_pyfunction!(dmvnorm_py, m)?)?;
    m.add_function(wrap_pyfunction!(me1e_ms_py, m)?)?;
    Ok(())
}

