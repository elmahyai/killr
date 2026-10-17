//! The new logspline fit of R package logspline 2.1.22, remade from
//! `src/nlsd.c`: `nlogcensorx` and `nlogcensor` (the model search), and
//! `rpqlsd` (density, distribution function, and quantiles).
//!
//! Copyright [1993-2018] Charles Kooperberg. Licensed under the Apache License,
//! Version 2.0, as stated in the header of the original file.

pub mod base;
mod fit;
mod iterate;
mod quad;
mod remove;
mod rpq;
mod setup;

pub use rpq::rpqlsd;

use base::{definespace, five, getsame, mat, mylog, DataS, Mat, MAXKNOTS};
use fit::nlsd;

/// Shared state of the C source: `ctheta`, `kints`, and `cuu` are file-scope
/// statics there, and they are read across the score and Rao routines.
pub struct Glob {
    pub ctheta: f64,
    pub kints: Mat,
    pub cuu: Vec<f64>,
}

/// `nlogcensorx`: report the maximum number of knots (`intpars[0]`).
pub fn nlogcensorx(intpars: &mut [i32]) {
    intpars[0] = MAXKNOTS as i32 + 5;
}

/// `nlogcensor`: fit the new logspline. Arguments follow the C `.C` interface:
/// `intpars` integer parameters, `data0` the uncensored data (and the output
/// coefficients on exit), `dpars` double parameters, `logs` the log-likelihood
/// of each model, `ad` the addition/deletion flag of each model, `kts` the knots.
pub fn nlogcensor(
    intpars: &mut [i32],
    data0: &mut [f64],
    dpars: &mut [f64],
    logs: &mut [f64],
    ad: &mut [i32],
    kts: &mut [f64],
) {
    // we only want parameters and leave...
    if intpars[0] < -10 {
        intpars[0] = MAXKNOTS as i32 + 5;
        return;
    }
    let ndata = intpars[0];
    let nd = ndata as usize;

    // define the data
    let mut same = vec![0i16; nd + 2];
    getsame(data0, nd, &mut same);
    let mut data = DataS {
        ndata,
        data: data0.to_vec(),
        idata: vec![0i32; nd + 1],
        same,
    };
    // allocate the space
    let mut spc = definespace(ndata);
    let mut g = Glob {
        ctheta: 0.0,
        kints: mat(spc.nip as usize + 11, 8),
        cuu: vec![0.0f64; MAXKNOTS + 6],
    };

    // the integer and double parameters
    let mut ndmax = intpars[1];
    let mut mind = intpars[6];
    if mind < 1 {
        mind = (2.5 * (ndata as f64).powf(0.2) + 0.5) as i32;
        if ndata / mind < 10 {
            mind = ndata / 10;
        }
        if mind < 3 {
            mind = 3;
        }
    }
    intpars[6] = mind;
    let mut strt = intpars[2];
    let silent = intpars[3];
    let mut alpha = dpars[0];
    if strt == 547 {
        strt = (2.5 * (intpars[0] as f64).powf(0.2)).floor() as i32;
        if strt > 25 {
            strt = 25;
        }
        if strt > intpars[0] / 4 {
            strt = intpars[0] / 4;
        }
    }
    if alpha < 0.0 {
        alpha = mylog(intpars[0] as f64);
    }
    spc.ilow = intpars[4];
    spc.iupp = intpars[5];
    spc.low = dpars[1];
    spc.upp = dpars[2];

    // starting knots
    if ndmax == 0 {
        ndmax = -((4.0 * (intpars[0] as f64).powf(0.2) + 1.0).floor() as i32);
    }
    if ndmax > MAXKNOTS as i32 {
        ndmax = MAXKNOTS as i32;
    }
    if strt <= 0 {
        if intpars[2] < 0 {
            intpars[2] = -intpars[2];
        } else {
            intpars[2] = (2.5 * (intpars[0] as f64).powf(0.2) + 1.0).floor() as i32;
        }
        if intpars[2] < 0 {
            intpars[2] = -intpars[2];
        }
        if intpars[2] < 3 {
            intpars[2] = 3;
        }
        let dat = data.data.clone();
        five(&dat, kts, intpars, &data.same);
        strt = intpars[2];
    }
    if ndmax > 0 && strt > ndmax + 1 {
        strt = ((ndmax + 3) as f64 / 2.0).floor() as i32;
    }
    if ndmax < 0 && strt > -ndmax {
        strt = ((3 - ndmax) as f64 / 2.0).floor() as i32;
    }
    // they were user provided
    if strt > 0 {
        spc.nk = strt;
        spc.ndim = strt - 1;
        for i in 0..strt as usize {
            spc.knots[i] = kts[i];
        }
        strt = 1;
        // find the iknots
        let mut j: usize = 0;
        let mut y = -(10f64.powf(100.0));
        let mut i: i64 = 0;
        while i < ndata as i64 {
            let x = data.data[i as usize];
            if y <= spc.knots[j] && x > spc.knots[j] {
                spc.iknots[j] = i as i32;
                j += 1;
                i -= 1;
                if j == spc.nk as usize {
                    i = ndata as i64 + 10;
                }
            } else {
                y = x;
            }
            i += 1;
        }
        if j as i32 == spc.nk - 1 {
            spc.iknots[(spc.nk - 1) as usize] = ndata - 1;
        }
        // two knots outside the range of the data is not allowed
        if (j as i32) < spc.nk - 1 {
            intpars[0] = 17;
            return;
        }
        if spc.iknots[1] == 0 {
            intpars[0] = 18;
            return;
        }
    }

    // do the work
    let rv = nlsd(&mut g, &mut spc, &mut data, alpha, ndmax, mind, strt, silent, logs, ad);
    intpars[0] = rv;
    dpars[0] = alpha;
    // output
    if intpars[0] > 0 && intpars[0] < 100 {
        return;
    }
    intpars[1] = spc.nk;
    intpars[2] = spc.ndim;
    for i in 0..(spc.nk + 2) as usize {
        data0[i] = 0.0;
        for j in 0..(spc.nk - 1) as usize {
            data0[i] += spc.basis[j].beta * spc.basis[j].c1[i];
        }
    }
    data0[0] += mylog(spc.cth);
    for i in 0..spc.nk as usize {
        kts[i] = spc.knots[i];
    }
}
