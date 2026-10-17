//! `UPDATEBOBYQA` from minqa `updatebobyqa.f`.

use crate::arr::{g, g2, s, s2};

pub fn update(
    n: i32,
    npt: i32,
    bmat: &mut [f64],
    zmat: &mut [f64],
    ndim: i32,
    vlag: &mut [f64],
    beta: f64,
    denom: f64,
    knew: i32,
    w: &mut [f64],
) {
    let one = 1.0;
    let zero = 0.0;
    let nptm = npt - n - 1;
    let mut ztest = zero;
    for k in 1..=npt {
        for j in 1..=nptm {
            ztest = crate::arr::dmax1(ztest, g2(zmat, npt, k, j).abs());
        }
    }
    ztest = 1.0e-20 * ztest;

    for j in 2..=nptm {
        if g2(zmat, npt, knew, j).abs() > ztest {
            let temp = (g2(zmat, npt, knew, 1) * g2(zmat, npt, knew, 1)
                + g2(zmat, npt, knew, j) * g2(zmat, npt, knew, j))
            .sqrt();
            let tempa = g2(zmat, npt, knew, 1) / temp;
            let tempb = g2(zmat, npt, knew, j) / temp;
            for i in 1..=npt {
                let z1 = g2(zmat, npt, i, 1);
                let zj = g2(zmat, npt, i, j);
                let temp = tempa * z1 + tempb * zj;
                s2(zmat, npt, i, j, tempa * zj - tempb * z1);
                s2(zmat, npt, i, 1, temp);
            }
        }
        s2(zmat, npt, knew, j, zero);
    }

    for i in 1..=npt {
        s(w, i, g2(zmat, npt, knew, 1) * g2(zmat, npt, i, 1));
    }
    let alpha = g(w, knew);
    let tau = g(vlag, knew);
    s(vlag, knew, g(vlag, knew) - one);

    let temp = denom.sqrt();
    let tempb = g2(zmat, npt, knew, 1) / temp;
    let tempa = tau / temp;
    for i in 1..=npt {
        s2(
            zmat,
            npt,
            i,
            1,
            tempa * g2(zmat, npt, i, 1) - tempb * g(vlag, i),
        );
    }

    for j in 1..=n {
        let jp = npt + j;
        s(w, jp, g2(bmat, ndim, knew, j));
        let tempa = (alpha * g(vlag, jp) - tau * g(w, jp)) / denom;
        let tempb = (-beta * g(w, jp) - tau * g(vlag, jp)) / denom;
        for i in 1..=jp {
            let updated = (g2(bmat, ndim, i, j) + tempa * g(vlag, i)) + tempb * g(w, i);
            s2(bmat, ndim, i, j, updated);
            if i > npt {
                s2(bmat, ndim, jp, i - npt, g2(bmat, ndim, i, j));
            }
        }
    }
}
