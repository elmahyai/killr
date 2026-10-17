use crate::util::{blas_matprod1, densout, densoutck, denspar, maxerr, neville, shift_buffer};

pub trait ModelFunc {
    fn derivs(&mut self, t: f64, y: &[f64], ff: &mut [f64], stage_col: i32, neq: usize, stage: usize);
}

pub struct StepTimings {
    pub prev: f64,
    pub curr: f64,
}

pub fn rk_auto<F: ModelFunc>(
    model: &mut F,
    fsal: i32,
    neq: usize,
    stage: usize,
    verbose: i32,
    nknots: i32,
    interpolate: bool,
    densetype: i32,
    maxsteps: i32,
    nt: usize,
    iknots: &mut i32,
    it: &mut i32,
    it_ext: &mut i32,
    it_tot: &mut i32,
    it_rej: &mut i32,
    istate: &mut [i32; 22],
    t: &mut f64,
    tmax: f64,
    hmin: f64,
    hmax: f64,
    alpha: f64,
    beta: f64,
    dt: &mut f64,
    errold: &mut f64,
    tt: &[f64],
    y0: &mut [f64],
    y1: &mut [f64],
    y2: &mut [f64],
    dy1: &mut [f64],
    dy2: &mut [f64],
    ff: &mut [f64],
    fj: &mut [f64],
    tmp: &mut [f64],
    rr: &mut [f64],
    a: &[f64],
    bb1: &[f64],
    bb2: &[f64],
    cc: &[f64],
    dd: &[f64],
    atol: &[f64],
    rtol: &[f64],
    yknots: &mut [f64],
    yout: &mut [f64],
    timings: &mut StepTimings,
) {
    const MINSCALE: f64 = 0.2;
    const MAXSCALE: f64 = 10.0;
    const SAFE: f64 = 0.9;

    let mut accept = false;
    let mut nreject = *it_rej;
    let mut ik = *iknots;
    let mut it_local = *it;
    let mut it_ext_local = *it_ext;
    let mut it_tot_local = *it_tot;
    let mut dt_local = *dt;
    let mut errold_local = *errold;
    let mut dtnew = dt_local;

    loop {
        if accept {
            timings.prev = timings.curr;
        }
        timings.curr = dt_local;

        let j1 = if fsal != 0 && accept {
            for i in 0..neq {
                ff[i] = ff[i + neq * (stage - 1)];
            }
            1
        } else {
            0
        };

        for j in j1..stage {
            for i in 0..neq {
                fj[i] = 0.0;
            }
            let mut k = 0;
            while k < j {
                for i in 0..neq {
                    fj[i] += a[j + stage * k] * ff[i + neq * k] * dt_local;
                }
                k += 1;
            }
            for i in 0..neq {
                tmp[i] = fj[i] + y0[i];
            }
            model.derivs(*t + dt_local * cc[j], &tmp, ff, j as i32, neq, stage);
        }

        blas_matprod1(ff, neq, stage, bb1, stage, 1, dy1);
        blas_matprod1(ff, neq, stage, bb2, stage, 1, dy2);

        it_tot_local += 1;
        for i in 0..neq {
            y1[i] = y0[i] + dt_local * dy1[i];
            y2[i] = y0[i] + dt_local * dy2[i];
        }

        let err = maxerr(y0, y1, y2, atol, rtol, neq);
        let mut dtnew = dt_local;
        if err == 0.0 {
            dtnew = dt_local * 10.0;
            if dtnew > hmax {
                dtnew = hmax;
            }
            errold_local = err.max(1e-4);
            accept = true;
        } else if err < 1.0 {
            if accept {
                let scale = (SAFE * err.powf(-alpha) * errold_local.powf(beta)).min(MAXSCALE);
                dtnew = (dt_local * scale).min(hmax);
            }
            errold_local = err.max(1e-4);
            accept = true;
        } else {
            nreject += 1;
            accept = false;
            dtnew = dt_local * (SAFE * err.powf(-alpha)).max(MINSCALE);
        }

        if dtnew < hmin {
            accept = true;
            if verbose != 0 {
                eprintln!("h < hmin");
            }
            istate[0] = -2;
            dtnew = hmin;
        }

        if accept {
            if interpolate {
                if densetype == 1 {
                    denspar(ff, y0, y2, dt_local, dd, neq, stage, rr);
                    let mut t_ext = tt[it_ext_local as usize];
                    while t_ext <= *t + dt_local {
                        densout(rr, *t, t_ext, dt_local, tmp, neq);
                        if (it_ext_local as usize) < nt {
                            yout[it_ext_local as usize] = t_ext;
                            for i in 0..neq {
                                yout[it_ext_local as usize + nt * (1 + i)] = tmp[i];
                            }
                        }
                        if (it_ext_local as usize) < nt - 1 {
                            it_ext_local += 1;
                            t_ext = tt[it_ext_local as usize];
                        } else {
                            break;
                        }
                    }
                } else if densetype == 2 {
                    model.derivs(*t + dt_local, y2, dy2, 0, neq, stage);
                    let mut t_ext = tt[it_ext_local as usize];
                    while t_ext <= *t + dt_local {
                        densoutck(*t, t_ext, dt_local, y0, ff, dy2, tmp, neq);
                        if (it_ext_local as usize) < nt {
                            yout[it_ext_local as usize] = t_ext;
                            for i in 0..neq {
                                yout[it_ext_local as usize + nt * (1 + i)] = tmp[i];
                            }
                        }
                        if (it_ext_local as usize) < nt - 1 {
                            it_ext_local += 1;
                            t_ext = tt[it_ext_local as usize];
                        } else {
                            break;
                        }
                    }
                    for i in 0..neq {
                        ff[i + neq * (stage - 1)] = dy2[i];
                    }
                } else {
                    let nk = nknots as usize;
                    yknots[ik as usize] = *t + dt_local;
                    for i in 0..neq {
                        yknots[ik as usize + nk * (1 + i)] = y2[i];
                    }
                    if ik < nknots - 1 {
                        ik += 1;
                    } else {
                        let mut t_ext = tt[it_ext_local as usize];
                        while t_ext <= *t + dt_local {
                            neville(
                                yknots,
                                &yknots[nk..],
                                t_ext,
                                tmp,
                                nk,
                                neq,
                            );
                            if (it_ext_local as usize) < nt {
                                yout[it_ext_local as usize] = t_ext;
                                for i in 0..neq {
                                    yout[it_ext_local as usize + nt * (1 + i)] = tmp[i];
                                }
                            }
                            if (it_ext_local as usize) < nt - 1 {
                                it_ext_local += 1;
                                t_ext = tt[it_ext_local as usize];
                            } else {
                                break;
                            }
                        }
                        shift_buffer(yknots, nk, neq + 1);
                    }
                }
            }
            *t += dt_local;
            it_local += 1;
            y0.copy_from_slice(y2);
        }

        dt_local = dtnew.min(tmax - *t);
        if it_ext_local as usize > nt {
            panic!("error in RK solver rk_auto: output buffer overflow");
        }
        if it_tot_local > maxsteps {
            istate[0] = -1;
            eprintln!(
                "Number of time steps {} exceeded maxsteps at t = {}",
                it_local, *t
            );
            break;
        }
        if *t >= tmax - 100.0 * f64::EPSILON * dt_local {
            break;
        }
    }

    *iknots = ik;
    *it = it_local;
    *it_ext = it_ext_local;
    *it_tot = it_tot_local;
    *it_rej = nreject;
    *dt = dtnew;
    *errold = errold_local;
}
