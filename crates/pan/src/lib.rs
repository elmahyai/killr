//! Farebrother's pan, ported from lmtest `src/pan.f`.
//!
//! The probability is that a weighted sum of squared standard normals is less
//! than `x` times the unweighted sum, plus `c`. For the Durbin-Watson test,
//! `a[0]` is the statistic and `a[1..]` are the eigenvalues.

/// `a` is Fortran `A(0:M)`: `a[0]` is `x`, and `a[1..=m]` are the weights.
pub fn pan(a: &[f64], c: f64, n: i32) -> f64 {
    let m = a.len() - 1;
    let zero = 0.0;
    let one = 1.0;
    let half = 0.5;
    let two = 2.0;

    let (mut h, mut k, i) = if a[1] > a[m] {
        (m as i32, -1, 1)
    } else {
        (1, 1, m as i32)
    };
    let x = a[0];

    // DO 10. After a finished loop, gfortran leaves the index one step past the end.
    let mut nu;
    let mut found = false;
    let mut cursor = h;
    loop {
        if k > 0 && cursor > i || k < 0 && cursor < i {
            nu = i + k;
            break;
        }
        nu = cursor;
        if a[nu as usize] >= x {
            found = true;
            break;
        }
        cursor += k;
    }
    if !found && c >= zero {
        return one;
    }
    if nu == h && c <= zero {
        return zero;
    }

    if k == 1 {
        nu -= 1;
    }
    h = m as i32 - nu;
    let mut y = if c == zero {
        (h - nu) as f64
    } else {
        c * (a[1] - a[m])
    };

    let d: i32;
    let mut j1: i32;
    let mut j2: i32;
    let mut j3: i32;
    let mut j4: i32;
    if y >= zero {
        d = 2;
        h = nu;
        k = -k;
        j1 = 0;
        j2 = 2;
        j3 = 3;
        j4 = 1;
    } else {
        d = -2;
        nu += 1;
        j1 = m as i32 - 2;
        j2 = m as i32 - 1;
        j3 = m as i32 + 1;
        j4 = m as i32;
    }

    let pin = two * one.atan() / (n as f64);
    let mut sum = half * ((k as f64) + 1.0);
    let mut sgn = (k as f64) / (n as f64);
    let n2 = n + n - 1;

    // DO 70. The index is unused; an odd h runs the body twice.
    let mut l1 = h - 2 * (h / 2);
    loop {
        if l1 < 0 {
            break;
        }
        let mut l2 = j2;
        loop {
            if d > 0 && l2 > nu || d < 0 && l2 < nu {
                break;
            }
            let mut sum1 = a[j4 as usize];
            let mut prod = a[l2 as usize];
            let u = half * (sum1 + prod);
            let v = half * (sum1 - prod);
            sum1 = zero;
            let mut step = 1;
            while step <= n2 {
                y = u - v * ((step as f64) * pin).cos();
                let num = y - x;
                prod = (-c / num).exp();
                let mut kk = 1;
                while kk <= j1 {
                    prod *= num / (y - a[kk as usize]);
                    kk += 1;
                }
                kk = j3;
                while kk <= m as i32 {
                    prod *= num / (y - a[kk as usize]);
                    kk += 1;
                }
                sum1 += prod.abs().sqrt();
                step += 2;
            }
            sgn = -sgn;
            sum += sgn * sum1;
            j1 += d;
            j3 += d;
            j4 += d;
            l2 += d;
        }
        if d == 2 {
            j3 -= 1;
        } else {
            j1 += 1;
        }
        j2 = 0;
        nu = 0;
        l1 -= 1;
    }
    sum
}

#[cfg(feature = "python")]
mod py {
    use pyo3::prelude::*;

    #[pyfunction]
    fn pan_prob(a: Vec<f64>, c: f64, n: i32) -> f64 {
        super::pan(&a, c, n)
    }

    #[pymodule]
    fn pan(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(pan_prob, m)?)?;
        Ok(())
    }
}
