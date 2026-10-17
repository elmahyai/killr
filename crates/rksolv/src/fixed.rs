use crate::auto::ModelFunc;
use crate::util::{blas_matprod1, neville, shift_buffer, sign};

pub fn rk_fixed<F: ModelFunc>(
    model: &mut F,
    neq: usize,
    stage: usize,
    verbose: i32,
    nknots: i32,
    interpolate: bool,
    maxsteps: i32,
    nt: usize,
    iknots: &mut i32,
    it: &mut i32,
    it_ext: &mut i32,
    it_tot: &mut i32,
    istate: &mut [i32; 22],
    t: &mut f64,
    tmax: f64,
    hini: f64,
    dt: &mut f64,
    tt: &[f64],
    y0: &mut [f64],
    y1: &mut [f64],
    dy1: &mut [f64],
    ff: &mut [f64],
    fj: &mut [f64],
    tmp: &mut [f64],
    a: &[f64],
    bb1: &[f64],
    cc: &[f64],
    yknots: &mut [f64],
    yout: &mut [f64],
    timings: &mut crate::auto::StepTimings,
) {
    let mut ik = *iknots;
    let mut it_local = *it;
    let mut it_ext_local = *it_ext;
    let mut it_tot_local = *it_tot;
    let mut dt_local = *dt;

    loop {
        if hini.abs() < f64::EPSILON * 100.0 {
            dt_local = tt[it_local as usize] - tt[it_local as usize - 1];
        } else {
            dt_local = hini.abs().min((tmax - *t).abs()) * sign(hini);
        }

        timings.prev = timings.curr;
        timings.curr = dt_local;

        for j in 0..stage {
            if j == 0 {
                for i in 0..neq {
                    fj[i] = 0.0;
                }
            } else {
                for i in 0..neq {
                    fj[i] = a[j] * ff[i + neq * (j - 1)] * dt_local;
                }
            }
            for i in 0..neq {
                tmp[i] = fj[i] + y0[i];
            }
            model.derivs(*t + dt_local * cc[j], &tmp, ff, j as i32, neq, stage);
        }

        blas_matprod1(ff, neq, stage, bb1, stage, 1, dy1);
        it_tot_local += 1;
        for i in 0..neq {
            y1[i] = y0[i] + dt_local * dy1[i];
        }

        if interpolate {
            let nk = nknots as usize;
            yknots[ik as usize] = *t + dt_local;
            for i in 0..neq {
                yknots[ik as usize + nk * (1 + i)] = y1[i];
            }
            if ik < nknots - 1 {
                ik += 1;
            } else {
                let mut t_ext = tt[it_ext_local as usize];
                while t_ext <= *t + dt_local {
                    neville(yknots, &yknots[nk..], t_ext, tmp, nk, neq);
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

        *t += dt_local;
        it_local += 1;
        y0.copy_from_slice(y1);

        if it_ext_local as usize > nt {
            panic!("error in RK solver rk_fixed: output buffer overflow");
        }
        if it_tot_local > maxsteps {
            istate[0] = -1;
            if verbose != 0 {
                eprintln!(
                    "Number of time steps {} exceeded maxsteps at t = {}",
                    it_local, t
                );
            }
            break;
        }
        if (*t - tmax).abs() <= 100.0 * f64::EPSILON {
            break;
        }
    }

    *iknots = ik;
    *it = it_local;
    *it_ext = it_ext_local;
    *it_tot = it_tot_local;
}
