//! H-matrix update, from minqa `update.f`.

use crate::fortran::{get, get2, set, set2};

pub(crate) fn update(
    n: i32,
    npt: i32,
    bmat: &mut [f64],
    zmat: &mut [f64],
    idz: &mut i32,
    ndim: i32,
    vlag: &mut [f64],
    beta: f64,
    knew: i32,
    w: &mut [f64],
) {
    let _ = ndim;
    let one = 1.0;
    let nptm = npt - n - 1;
    let mut jl = 1;
    for j in 2..=nptm {
        if j == *idz {
            jl = *idz;
        } else if get2(zmat, npt, knew, j) != 0.0 {
            let mut temp = (get2(zmat, npt, knew, jl) * get2(zmat, npt, knew, jl)
                + get2(zmat, npt, knew, j) * get2(zmat, npt, knew, j))
            .sqrt();
            let tempa = get2(zmat, npt, knew, jl) / temp;
            let tempb = get2(zmat, npt, knew, j) / temp;
            for i in 1..=npt {
                temp = tempa * get2(zmat, npt, i, jl) + tempb * get2(zmat, npt, i, j);
                set2(
                    zmat,
                    npt,
                    i,
                    j,
                    tempa * get2(zmat, npt, i, j) - tempb * get2(zmat, npt, i, jl),
                );
                set2(zmat, npt, i, jl, temp);
            }
            set2(zmat, npt, knew, j, 0.0);
        }
    }

    let mut tempa = get2(zmat, npt, knew, 1);
    if *idz >= 2 {
        tempa = -tempa;
    }
    let tempb = if jl > 1 {
        get2(zmat, npt, knew, jl)
    } else {
        0.0
    };
    for i in 1..=npt {
        set(w, i, tempa * get2(zmat, npt, i, 1));
        if jl > 1 {
            set(w, i, get(w, i) + tempb * get2(zmat, npt, i, jl));
        }
    }
    let alpha = get(w, knew);
    let tau = get(vlag, knew);
    let tausq = tau * tau;
    let denom = alpha * beta + tausq;
    set(vlag, knew, get(vlag, knew) - one);

    let mut iflag = 0;
    if jl == 1 {
        let temp = denom.abs().sqrt();
        let tempb = tempa / temp;
        let tempa = tau / temp;
        for i in 1..=npt {
            set2(
                zmat,
                npt,
                i,
                1,
                tempa * get2(zmat, npt, i, 1) - tempb * get(vlag, i),
            );
        }
        if *idz == 1 && temp < 0.0 {
            *idz = 2;
        }
        if *idz >= 2 && temp >= 0.0 {
            iflag = 1;
        }
    } else {
        let mut ja = 1;
        if beta >= 0.0 {
            ja = jl;
        }
        let jb = jl + 1 - ja;
        let mut temp = get2(zmat, npt, knew, jb) / denom;
        let tempa = temp * beta;
        let tempb = temp * tau;
        temp = get2(zmat, npt, knew, ja);
        let scala = one / (beta.abs() * temp * temp + tausq).sqrt();
        let scalb = scala * denom.abs().sqrt();
        for i in 1..=npt {
            set2(
                zmat,
                npt,
                i,
                ja,
                scala * (tau * get2(zmat, npt, i, ja) - temp * get(vlag, i)),
            );
            set2(
                zmat,
                npt,
                i,
                jb,
                scalb * (get2(zmat, npt, i, jb) - tempa * get(w, i) - tempb * get(vlag, i)),
            );
        }
        if denom <= 0.0 {
            if beta < 0.0 {
                *idz += 1;
            }
            if beta >= 0.0 {
                iflag = 1;
            }
        }
    }

    if iflag == 1 {
        *idz -= 1;
        for i in 1..=npt {
            let temp = get2(zmat, npt, i, 1);
            set2(zmat, npt, i, 1, get2(zmat, npt, i, *idz));
            set2(zmat, npt, i, *idz, temp);
        }
    }

    for j in 1..=n {
        let jp = npt + j;
        set(w, jp, get2(bmat, ndim, knew, j));
        let tempa = (alpha * get(vlag, jp) - tau * get(w, jp)) / denom;
        let tempb = (-beta * get(w, jp) - tau * get(vlag, jp)) / denom;
        for i in 1..=jp {
            set2(
                bmat,
                ndim,
                i,
                j,
                get2(bmat, ndim, i, j) + tempa * get(vlag, i) + tempb * get(w, i),
            );
            if i > npt {
                set2(bmat, ndim, jp, i - npt, get2(bmat, ndim, i, j));
            }
        }
    }
}
