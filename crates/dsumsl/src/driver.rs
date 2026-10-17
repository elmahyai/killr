//! Reverse-communication driver for `DSUMSL` / `DSMSNO` (`dsumsl.f`).

use crate::blas_ref::{d1mach, dmax1};
use crate::linalg::{dlitvm, dlivmu, dltvmu, dlupdt, dlvmul, dwzbfg};
use crate::work::{ddeflt, dparck, Work};

const IV_CNVCOD: i32 = 55;
const IV_DG: i32 = 37;
const IV_G: i32 = 28;
const IV_G0: i32 = 48;
const IV_INITH: i32 = 25;
const IV_IRC: i32 = 29;
const IV_KAGQT: i32 = 33;
const IV_LMAT: i32 = 42;
const IV_MLSTGD: i32 = 32;
const IV_MODE: i32 = 35;
const IV_MODEL: i32 = 5;
const IV_MXFCAL: i32 = 17;
const IV_MXITER: i32 = 18;
const IV_NEXTV: i32 = 47;
const IV_NFCALL: i32 = 6;
const IV_NFGCAL: i32 = 7;
const IV_NGCALL: i32 = 30;
const IV_NITER: i32 = 31;
const IV_NWTSTP: i32 = 34;
const IV_RADINC: i32 = 8;
const IV_RESTOR: i32 = 9;
const IV_SGIRC: i32 = 57;
const IV_STAGE: i32 = 10;
const IV_STEP: i32 = 40;
const IV_STGLIM: i32 = 11;
const IV_STLSTG: i32 = 41;
const IV_SWITCH: i32 = 12;
const IV_TOOBIG: i32 = 2;
const IV_VNEED: i32 = 4;
const IV_X0: i32 = 43;
const IV_XIRC: i32 = 13;

const V_AFCTOL: i32 = 31;
const V_BIAS: i32 = 43;
const V_DECFAC: i32 = 22;
const V_DGNORM: i32 = 1;
const V_DINIT: i32 = 38;
const V_DST0: i32 = 3;
const V_DSTNRM: i32 = 2;
const V_DSTSAV: i32 = 18;
const V_ETA0: i32 = 42;
const V_F: i32 = 10;
const V_F0: i32 = 13;
const V_FDIF: i32 = 11;
const V_FLSTGD: i32 = 12;
const V_GRDFAC: i32 = 45;
const V_GTHG: i32 = 44;
const V_GTSTEP: i32 = 4;
const V_GTSLST: i32 = 14;
const V_INCFAC: i32 = 23;
const V_LMAX0: i32 = 35;
const V_LMAXS: i32 = 36;
const V_NREDUC: i32 = 6;
const V_NWTFAC: i32 = 46;
const V_PLSTGD: i32 = 15;
const V_PREDUC: i32 = 7;
const V_RAD0: i32 = 9;
const V_RADFAC: i32 = 16;
const V_RADIUS: i32 = 8;
const V_RDFCMN: i32 = 24;
const V_RDFCMX: i32 = 25;
const V_RELDX: i32 = 17;
const V_RFCTOL: i32 = 32;
const V_SCTOL: i32 = 37;
const V_STPPAR: i32 = 5;
const V_TUNER1: i32 = 26;
const V_TUNER2: i32 = 27;
const V_TUNER3: i32 = 28;
const V_TUNER4: i32 = 29;
const V_TUNER5: i32 = 30;
const V_XCTOL: i32 = 33;
const V_XFTOL: i32 = 34;

fn drelst(w: &Work, x0: i32) -> f64 {
    let mut emax = 0.0;
    let mut xmax = 0.0;
    for i in 1..=w.n {
        let t = (w.dg(i) * (w.xg(i) - w.av(x0, i))).abs();
        if emax < t {
            emax = t;
        }
        let t = w.dg(i) * (w.xg(i).abs() + w.av(x0, i).abs());
        if xmax < t {
            xmax = t;
        }
    }
    if xmax > 0.0 { emax / xmax } else { 0.0 }
}

fn ddbdog(w: &mut Work, dig: i32, g: i32, nwt: i32, step: i32) {
    let n = w.n;
    let nwtnrm = w.vg(V_DST0);
    let mut rlambd = 1.0;
    if nwtnrm > 0.0 {
        rlambd = w.vg(V_RADIUS) / nwtnrm;
    }
    let gnorm = w.vg(V_DGNORM);
    for i in 1..=n {
        w.sv(step, i, w.av(g, i) / gnorm);
    }
    let ghinvg = w.dotv(n, step, nwt);
    w.vs(V_NREDUC, 0.5 * ghinvg * gnorm);
    w.vs(V_GRDFAC, 0.0);
    w.vs(V_NWTFAC, 0.0);
    if rlambd >= 1.0 {
        w.vs(V_STPPAR, 0.0);
        w.vs(V_DSTNRM, nwtnrm);
        w.vs(V_GTSTEP, -ghinvg * gnorm);
        w.vs(V_PREDUC, w.vg(V_NREDUC));
        w.vs(V_NWTFAC, -1.0);
        for i in 1..=n {
            w.sv(step, i, -w.av(nwt, i));
        }
        return;
    }
    w.vs(V_DSTNRM, w.vg(V_RADIUS));
    let gthg = w.vg(V_GTHG);
    let cfact = (gnorm / gthg) * (gnorm / gthg);
    let cnorm = gnorm * cfact;
    let relax = 1.0 - w.vg(V_BIAS) * (1.0 - cnorm / ghinvg);
    if rlambd >= relax {
        w.vs(V_STPPAR, 1.0 - (rlambd - relax) / (1.0 - relax));
        let t = -rlambd;
        w.vs(V_GTSTEP, t * ghinvg * gnorm);
        w.vs(V_PREDUC, rlambd * (1.0 - 0.5 * rlambd) * ghinvg * gnorm);
        w.vs(V_NWTFAC, t);
        for i in 1..=n {
            w.sv(step, i, t * w.av(nwt, i));
        }
        return;
    }
    if cnorm >= w.vg(V_RADIUS) {
        let t = -w.vg(V_RADIUS) / gnorm;
        w.vs(V_GRDFAC, t);
        w.vs(V_STPPAR, 1.0 + cnorm / w.vg(V_RADIUS));
        w.vs(V_GTSTEP, -w.vg(V_RADIUS) * gnorm);
        let radius = w.vg(V_RADIUS);
        w.vs(
            V_PREDUC,
            radius * (gnorm - 0.5 * radius * (gthg / gnorm) * (gthg / gnorm)),
        );
        for i in 1..=n {
            w.sv(step, i, t * w.av(dig, i));
        }
        return;
    }
    let ctrnwt = cfact * relax * ghinvg / gnorm;
    let t1 = ctrnwt - cfact * cfact;
    let radius = w.vg(V_RADIUS);
    let t2 = (radius / gnorm) * (radius / gnorm) - cfact * cfact;
    let femnsq = (relax * nwtnrm / gnorm) * (relax * nwtnrm / gnorm) - ctrnwt - t1;
    let t = t2 / (t1 + (t1 * t1 + femnsq * t2).sqrt());
    let gr = (t - 1.0) * cfact;
    w.vs(V_GRDFAC, gr);
    let nw = -t * relax;
    w.vs(V_NWTFAC, nw);
    w.vs(V_STPPAR, 2.0 - t);
    w.vs(V_GTSTEP, gnorm * (gr * gnorm + nw * ghinvg));
    w.vs(
        V_PREDUC,
        -(gr * gnorm) * ((nw + 1.0) * gnorm)
            - (nw * gnorm) * (1.0 + 0.5 * nw) * ghinvg
            - 0.5 * (gthg * gr) * (gthg * gr),
    );
    for i in 1..=n {
        w.sv(step, i, gr * w.av(dig, i) + nw * w.av(nwt, i));
    }
}

fn dassst(w: &mut Work, step: i32, stlstg: i32, x0: i32) {
    let mut nfc = w.ig(IV_NFCALL);
    w.iset(IV_SWITCH, 0);
    w.iset(IV_RESTOR, 0);
    let mut rfac1 = 1.0;
    let mut goodx = true;
    let mut reldx1 = 0.0;
    let mut emax = 0.0;
    let mut emaxs = 0.0;
    let i_entry = w.ig(IV_IRC);
    let mut label = 0i32;
    loop {
        match label {
            0 => {
                if (1..=12).contains(&i_entry) {
                    label = match i_entry {
                        1 => 20,
                        2 => 30,
                        3 | 4 => 10,
                        5 => 40,
                        6 => 280,
                        7..=11 => 220,
                        12 => 170,
                        _ => 0,
                    };
                    continue;
                }
                w.iset(IV_IRC, 13);
                return;
            }
            10 => {
                w.iset(IV_STAGE, 1);
                w.iset(IV_RADINC, 0);
                w.vs(V_FLSTGD, w.vg(V_F0));
                if w.ig(IV_TOOBIG) == 0 {
                    label = 90;
                    continue;
                }
                w.iset(IV_STAGE, -1);
                w.iset(IV_XIRC, i_entry);
                label = 60;
            }
            20 => {
                if w.ig(IV_MODEL) == w.ig(IV_MLSTGD) {
                    w.iset(IV_STAGE, w.ig(IV_STGLIM));
                    w.iset(IV_RADINC, -1);
                    label = 90;
                    continue;
                }
                label = 30;
            }
            30 => {
                w.iset(IV_STAGE, w.ig(IV_STAGE) + 1);
                label = 40;
            }
            40 => {
                if w.ig(IV_STAGE) > 0 {
                    label = 50;
                    continue;
                }
                if w.ig(IV_TOOBIG) != 0 {
                    label = 60;
                    continue;
                }
                w.iset(IV_STAGE, -w.ig(IV_STAGE));
                let i = w.ig(IV_XIRC);
                label = match i {
                    1 => 20,
                    2 => 30,
                    3 | 4 => 90,
                    5 => 70,
                    _ => 50,
                };
                // Fortran falls out of the computed jumps into the next
                // statement only when none of 1..5 match. That next statement
                // is label 50's test, so an unmatched I continues at 50.
                if !matches!(i, 1 | 2 | 3 | 4 | 5) {
                    label = 50;
                }
            }
            50 => {
                if w.ig(IV_TOOBIG) == 0 {
                    label = 70;
                    continue;
                }
                if w.ig(IV_RADINC) > 0 {
                    label = 80;
                    continue;
                }
                w.iset(IV_STAGE, -w.ig(IV_STAGE));
                w.iset(IV_XIRC, w.ig(IV_IRC));
                label = 60;
            }
            60 => {
                w.vs(V_RADFAC, w.vg(V_DECFAC));
                w.iset(IV_RADINC, w.ig(IV_RADINC) - 1);
                w.iset(IV_IRC, 5);
                return;
            }
            70 => {
                if w.vg(V_F) < w.vg(V_FLSTGD) {
                    label = 90;
                    continue;
                }
                if w.ig(IV_MODEL) != w.ig(IV_MLSTGD) {
                    w.iset(IV_MODEL, w.ig(IV_MLSTGD));
                    w.iset(IV_SWITCH, 1);
                }
                label = 80;
            }
            80 => {
                if w.vg(V_FLSTGD) < w.vg(V_F0) {
                    w.iset(IV_RESTOR, 1);
                    w.vs(V_F, w.vg(V_FLSTGD));
                    w.vs(V_PREDUC, w.vg(V_PLSTGD));
                    w.vs(V_GTSTEP, w.vg(V_GTSLST));
                    if w.ig(IV_SWITCH) == 0 {
                        rfac1 = w.vg(V_DSTNRM) / w.vg(V_DSTSAV);
                    }
                    w.vs(V_DSTNRM, w.vg(V_DSTSAV));
                    nfc = w.ig(IV_NFGCAL);
                    goodx = false;
                }
                label = 90;
            }
            90 => {
                reldx1 = drelst(w, x0);
                if !goodx {
                    for i in 1..=w.n {
                        let st = w.av(stlstg, i);
                        w.sv(step, i, st);
                        w.xs(i, w.av(x0, i) + st);
                    }
                }
                label = 110;
            }
            110 => {
                w.vs(V_FDIF, w.vg(V_F0) - w.vg(V_F));
                if w.vg(V_FDIF) > w.vg(V_TUNER2) * w.vg(V_PREDUC) {
                    label = 140;
                    continue;
                }
                w.vs(V_RELDX, reldx1);
                if w.vg(V_F) >= w.vg(V_F0) {
                    w.iset(IV_MLSTGD, w.ig(IV_MODEL));
                    w.vs(V_FLSTGD, w.vg(V_F));
                    w.vs(V_F, w.vg(V_F0));
                    w.copy_v_to_x(w.n, x0);
                    w.iset(IV_RESTOR, 1);
                    label = 130;
                    continue;
                }
                w.iset(IV_NFGCAL, nfc);
                label = 130;
            }
            130 => {
                w.iset(IV_IRC, 1);
                if w.ig(IV_STAGE) >= w.ig(IV_STGLIM) {
                    w.iset(IV_IRC, 5);
                    w.iset(IV_RADINC, w.ig(IV_RADINC) - 1);
                }
                label = 160;
            }
            140 => {
                w.iset(IV_NFGCAL, nfc);
                rfac1 = 1.0;
                if goodx {
                    w.vs(V_RELDX, reldx1);
                }
                w.vs(V_DSTSAV, w.vg(V_DSTNRM));
                if w.vg(V_FDIF) > w.vg(V_PREDUC) * w.vg(V_TUNER1) {
                    label = 190;
                    continue;
                }
                if w.ig(IV_STAGE) < w.ig(IV_STGLIM) {
                    w.iset(IV_IRC, 2);
                    label = 160;
                    continue;
                }
                w.iset(IV_IRC, 4);
                label = 160;
            }
            160 => {
                w.iset(IV_XIRC, w.ig(IV_IRC));
                emax = w.vg(V_GTSTEP) + w.vg(V_FDIF);
                w.vs(V_RADFAC, 0.5 * rfac1);
                if emax < w.vg(V_GTSTEP) {
                    let rad = rfac1
                        * dmax1(w.vg(V_RDFCMN), 0.5 * w.vg(V_GTSTEP) / emax);
                    w.vs(V_RADFAC, rad);
                }
                label = 170;
            }
            170 => {
                if w.vg(V_RELDX) > w.vg(V_XFTOL) {
                    w.iset(IV_IRC, w.ig(IV_XIRC));
                    if w.vg(V_F) < w.vg(V_F0) {
                        label = 200;
                        continue;
                    }
                    label = 230;
                    continue;
                }
                w.iset(IV_IRC, 12);
                label = 240;
            }
            180 => {
                w.iset(IV_IRC, 12);
                label = 240;
            }
            190 => {
                if w.vg(V_FDIF) < (-w.vg(V_TUNER3) * w.vg(V_GTSTEP)) {
                    label = 210;
                    continue;
                }
                if w.ig(IV_RADINC) < 0 || w.ig(IV_RESTOR) == 1 {
                    label = 210;
                    continue;
                }
                w.vs(V_RADFAC, w.vg(V_RDFCMX));
                let gts = w.vg(V_GTSTEP);
                let radfac = w.vg(V_RADFAC);
                if w.vg(V_FDIF) < (0.5 / radfac - 1.0) * gts {
                    let rad = dmax1(w.vg(V_INCFAC), 0.5 * gts / (gts + w.vg(V_FDIF)));
                    w.vs(V_RADFAC, rad);
                }
                w.iset(IV_IRC, 4);
                if w.vg(V_STPPAR) == 0.0 {
                    label = 230;
                    continue;
                }
                w.iset(IV_IRC, 5);
                w.iset(IV_RADINC, w.ig(IV_RADINC) + 1);
                label = 200;
            }
            200 => {
                w.vs(V_FLSTGD, w.vg(V_F));
                w.iset(IV_MLSTGD, w.ig(IV_MODEL));
                w.copy_vv(w.n, step, stlstg);
                w.vs(V_DSTSAV, w.vg(V_DSTNRM));
                w.iset(IV_NFGCAL, nfc);
                w.vs(V_PLSTGD, w.vg(V_PREDUC));
                w.vs(V_GTSLST, w.vg(V_GTSTEP));
                label = 230;
            }
            210 => {
                w.vs(V_RADFAC, 1.0);
                w.iset(IV_IRC, 3);
                label = 230;
            }
            220 => {
                w.iset(IV_IRC, w.ig(IV_XIRC));
                if w.vg(V_DSTSAV) < 0.0 {
                    w.iset(IV_IRC, 12);
                }
                label = 240;
            }
            230 => {
                w.iset(IV_XIRC, w.ig(IV_IRC));
                label = 240;
            }
            240 => {
                if w.vg(V_F).abs() < w.vg(V_AFCTOL) {
                    w.iset(IV_IRC, 10);
                }
                if 0.5 * w.vg(V_FDIF) > w.vg(V_PREDUC) {
                    return;
                }
                emax = w.vg(V_RFCTOL) * w.vg(V_F0).abs();
                emaxs = w.vg(V_SCTOL) * w.vg(V_F0).abs();
                if w.vg(V_DSTNRM) > w.vg(V_LMAXS) && w.vg(V_PREDUC) <= emaxs {
                    w.iset(IV_IRC, 11);
                }
                if w.vg(V_DST0) < 0.0 {
                    label = 250;
                    continue;
                }
                let mut i = 0i32;
                let nreduc = w.vg(V_NREDUC);
                if (nreduc > 0.0 && nreduc <= emax) || (nreduc == 0.0 && w.vg(V_PREDUC) == 0.0) {
                    i = 2;
                }
                if w.vg(V_STPPAR) == 0.0 && w.vg(V_RELDX) <= w.vg(V_XCTOL) && goodx {
                    i += 1;
                }
                if i > 0 {
                    w.iset(IV_IRC, i + 6);
                }
                label = 250;
            }
            250 => {
                if w.ig(IV_IRC) > 5 && w.ig(IV_IRC) != 12 {
                    return;
                }
                if w.vg(V_DSTNRM) <= w.vg(V_LMAXS) {
                    if w.vg(V_PREDUC) >= emaxs {
                        return;
                    }
                    if w.vg(V_DST0) > 0.0 && 0.5 * w.vg(V_DST0) <= w.vg(V_LMAXS) {
                        return;
                    }
                    label = 270;
                    continue;
                }
                if 0.5 * w.vg(V_DSTNRM) <= w.vg(V_LMAXS) {
                    return;
                }
                let xmax = w.vg(V_LMAXS) / w.vg(V_DSTNRM);
                if xmax * (2.0 - xmax) * w.vg(V_PREDUC) >= emaxs {
                    return;
                }
                label = 270;
            }
            270 => {
                if w.vg(V_NREDUC) < 0.0 {
                    label = 290;
                    continue;
                }
                w.vs(V_GTSLST, w.vg(V_GTSTEP));
                w.vs(V_DSTSAV, w.vg(V_DSTNRM));
                if w.ig(IV_IRC) == 12 {
                    w.vs(V_DSTSAV, -w.vg(V_DSTSAV));
                }
                w.vs(V_PLSTGD, w.vg(V_PREDUC));
                w.iset(IV_IRC, 6);
                w.copy_vv(w.n, step, stlstg);
                return;
            }
            280 => {
                w.vs(V_GTSTEP, w.vg(V_GTSLST));
                w.vs(V_DSTNRM, w.vg(V_DSTSAV).abs());
                w.copy_vv(w.n, stlstg, step);
                w.iset(IV_IRC, w.ig(IV_XIRC));
                if w.vg(V_DSTSAV) <= 0.0 {
                    w.iset(IV_IRC, 12);
                }
                w.vs(V_NREDUC, -w.vg(V_PREDUC));
                w.vs(V_PREDUC, w.vg(V_PLSTGD));
                label = 290;
            }
            290 => {
                if -w.vg(V_NREDUC) <= w.vg(V_RFCTOL) * w.vg(V_F0).abs() {
                    w.iset(IV_IRC, 11);
                }
                return;
            }
            _ => panic!("dassst label {label}"),
        }
    }
}

fn ditsum(w: &Work) {
    // Printing. With PRUNIT = 0 (garch trace = false) this is a no-op.
    // The counters it would touch are not read by the step.
    if w.ig(21) == 0 {
        return;
    }
}

fn dsumit(w: &mut Work) {
    let n = w.n;
    let mut label = 0i32;
    loop {
        match label {
            0 => {
                let i = w.ig(1);
                if i == 1 {
                    label = 40;
                    continue;
                }
                if i == 2 {
                    label = 50;
                    continue;
                }
                if w.ig(1) == 0 {
                    ddeflt(w, 2);
                }
                w.iset(IV_VNEED, w.ig(IV_VNEED) + n * (n + 13) / 2);
                dparck(w, 2);
                let i = w.ig(1) - 2;
                if i > 12 {
                    return;
                }
                if i < 7 {
                    label = 160;
                    continue;
                }
                if i == 7 || i == 9 {
                    label = 110;
                    continue;
                }
                if i == 8 {
                    label = 80;
                    continue;
                }
                if i == 12 {
                    label = 20;
                    continue;
                }
                let nn1o2 = n * (n + 1) / 2;
                let l = w.ig(IV_LMAT);
                w.iset(IV_X0, l + nn1o2);
                w.iset(IV_STEP, w.ig(IV_X0) + n);
                w.iset(IV_STLSTG, w.ig(IV_STEP) + n);
                w.iset(IV_G0, w.ig(IV_STLSTG) + n);
                w.iset(IV_NWTSTP, w.ig(IV_G0) + n);
                w.iset(IV_DG, w.ig(IV_NWTSTP) + n);
                w.iset(IV_NEXTV, w.ig(IV_DG) + n);
                if w.ig(1) != 13 {
                    label = 20;
                    continue;
                }
                w.iset(1, 14);
                return;
            }
            20 => {
                w.iset(IV_NITER, 0);
                w.iset(IV_NFCALL, 1);
                w.iset(IV_NGCALL, 1);
                w.iset(IV_NFGCAL, 1);
                w.iset(IV_MODE, -1);
                w.iset(IV_MODEL, 1);
                w.iset(IV_STGLIM, 1);
                w.iset(IV_TOOBIG, 0);
                w.iset(IV_CNVCOD, 0);
                w.iset(IV_RADINC, 0);
                w.vs(V_RAD0, 0.0);
                if w.vg(V_DINIT) >= 0.0 {
                    for i in 1..=n {
                        w.d[i as usize] = w.vg(V_DINIT);
                    }
                }
                w.iset(1, 1);
                if w.ig(IV_INITH) != 1 {
                    return;
                }
                let l = w.ig(IV_LMAT);
                let nn1o2 = n * (n + 1) / 2;
                w.fill_v(nn1o2, l, 0.0);
                let mut k = l - 1;
                for i in 1..=n {
                    k += i;
                    let mut t = w.dg(i);
                    if t <= 0.0 {
                        t = 1.0;
                    }
                    w.vs(k, t);
                }
                return;
            }
            40 => {
                w.vs(V_F, w.fx);
                if w.ig(IV_MODE) >= 0 {
                    label = 160;
                    continue;
                }
                w.iset(1, 2);
                if w.ig(IV_TOOBIG) == 0 {
                    return;
                }
                w.iset(1, 63);
                label = 270;
            }
            50 => {
                if w.ig(IV_NFGCAL) == 0 {
                    w.iset(1, 65);
                    label = 270;
                    continue;
                }
                let dg1 = w.ig(IV_DG);
                w.vvmup(n, dg1, w.g1, false, false);
                let gnorm = w.nrm(n, dg1);
                w.vs(V_DGNORM, gnorm);
                if w.ig(IV_CNVCOD) != 0 {
                    label = 260;
                    continue;
                }
                if w.ig(IV_MODE) == 0 {
                    label = 220;
                    continue;
                }
                w.vs(V_RADFAC, w.vg(V_LMAX0));
                w.vs(V_DSTNRM, 1.0);
                w.iset(IV_MODE, 0);
                label = 70;
            }
            70 => {
                ditsum(w);
                label = 80;
            }
            80 => {
                let k = w.ig(IV_NITER);
                if k >= w.ig(IV_MXITER) {
                    w.iset(1, 10);
                    label = 270;
                    continue;
                }
                label = 90;
                // carry k via IV
                w.iset(IV_NITER, k);
            }
            90 => {
                let k = w.ig(IV_NITER);
                w.iset(IV_NITER, k + 1);
                w.vs(V_RADIUS, w.vg(V_RADFAC) * w.vg(V_DSTNRM));
                let g01 = w.ig(IV_G0);
                let x01 = w.ig(IV_X0);
                w.vs(V_F0, w.vg(V_F));
                w.iset(IV_IRC, 4);
                w.iset(IV_KAGQT, -1);
                w.copy_x_to_v(n, x01);
                w.copy_vv(n, w.g1, g01);
                label = 100;
            }
            100 => {
                // DSTOPX is false in this port of the tseries source.
                label = 120;
            }
            110 => {
                if w.vg(V_F) < w.vg(V_F0) {
                    w.vs(V_RADFAC, 1.0);
                    label = 90;
                    continue;
                }
                label = 120;
            }
            120 => {
                if w.ig(IV_NFCALL) < w.ig(IV_MXFCAL) {
                    label = 140;
                    continue;
                }
                w.iset(1, 9);
                label = 130;
            }
            130 => {
                if w.vg(V_F) >= w.vg(V_F0) {
                    label = 270;
                    continue;
                }
                w.iset(IV_CNVCOD, w.ig(1));
                label = 210;
            }
            140 => {
                let step1 = w.ig(IV_STEP);
                let dg1 = w.ig(IV_DG);
                let nwt = w.ig(IV_NWTSTP);
                if w.ig(IV_KAGQT) < 0 {
                    let l = w.ig(IV_LMAT);
                    dlivmu(w, nwt, l, w.g1);
                    dlitvm(w, nwt, l, nwt);
                    w.vvmup(n, step1, nwt, false, true);
                    w.vs(V_DST0, w.nrm(n, step1));
                    w.vvmup(n, dg1, dg1, false, false);
                    dltvmu(w, step1, l, dg1);
                    w.vs(V_GTHG, w.nrm(n, step1));
                    w.iset(IV_KAGQT, 0);
                }
                ddbdog(w, dg1, w.g1, nwt, step1);
                if w.ig(IV_IRC) == 6 {
                    label = 160;
                    continue;
                }
                let x01 = w.ig(IV_X0);
                let step1 = w.ig(IV_STEP);
                w.vaxpy_x(n, 1.0, step1, x01);
                w.iset(IV_NFCALL, w.ig(IV_NFCALL) + 1);
                w.iset(1, 1);
                w.iset(IV_TOOBIG, 0);
                return;
            }
            160 => {
                let step1 = w.ig(IV_STEP);
                let lst = w.ig(IV_STLSTG);
                let x01 = w.ig(IV_X0);
                dassst(w, step1, lst, x01);
                let k = w.ig(IV_IRC);
                label = match k {
                    1 | 5 => 170,
                    2 | 3 | 4 => 200,
                    6 => 180,
                    7..=12 => 190,
                    13 => 250,
                    14 => 220,
                    _ => 170,
                };
            }
            170 => {
                w.vs(V_RADIUS, w.vg(V_RADFAC) * w.vg(V_DSTNRM));
                label = 100;
            }
            180 => {
                w.vs(V_RADIUS, w.vg(V_LMAX0));
                label = 140;
            }
            190 => {
                let k = w.ig(IV_IRC);
                w.iset(IV_CNVCOD, k - 4);
                if w.vg(V_F) >= w.vg(V_F0) || w.ig(IV_XIRC) == 14 {
                    label = 260;
                    continue;
                }
                w.iset(IV_XIRC, 14);
                label = 200;
            }
            200 => {
                if w.ig(IV_IRC) == 3 {
                    let step1 = w.ig(IV_STEP);
                    let temp1 = w.ig(IV_STLSTG);
                    let l = w.ig(IV_LMAT);
                    dltvmu(w, temp1, l, step1);
                    dlvmul(w, temp1, l, temp1);
                }
                label = 210;
            }
            210 => {
                w.iset(IV_NGCALL, w.ig(IV_NGCALL) + 1);
                w.iset(1, 2);
                return;
            }
            220 => {
                let g01 = w.ig(IV_G0);
                w.vaxpy_vv(n, g01, -1.0, g01, w.g1);
                let step1 = w.ig(IV_STEP);
                let temp1 = w.ig(IV_STLSTG);
                if w.ig(IV_IRC) == 3 {
                    w.vaxpy_vv(n, temp1, -1.0, g01, temp1);
                    w.vvmup(n, temp1, temp1, false, false);
                    let big_step = w.nrm(n, temp1) > w.vg(V_DGNORM) * w.vg(V_TUNER4);
                    let uphill = w.dotv(n, w.g1, step1) >= w.vg(V_GTSTEP) * w.vg(V_TUNER5);
                    if !(big_step && uphill) {
                        w.vs(V_RADFAC, w.vg(V_INCFAC));
                    }
                }
                label = 240;
            }
            240 => {
                let step1 = w.ig(IV_STEP);
                let g01 = w.ig(IV_G0);
                let temp1 = w.ig(IV_STLSTG);
                let wv = w.ig(IV_NWTSTP);
                let z = w.ig(IV_X0);
                let l = w.ig(IV_LMAT);
                dwzbfg(w, l, step1, wv, g01, z);
                dlupdt(w, temp1, step1, l, g01, wv, z);
                w.iset(1, 2);
                label = 70;
            }
            250 => {
                w.iset(1, 64);
                label = 260;
            }
            260 => {
                w.iset(1, w.ig(IV_CNVCOD));
                w.iset(IV_CNVCOD, 0);
                label = 270;
            }
            270 => {
                ditsum(w);
                return;
            }
            _ => panic!("dsumit label {label}"),
        }
    }
}

pub fn dsumsl(
    w: &mut Work,
    mut calcf: impl FnMut(&mut Work, &mut i32),
    mut calcg: impl FnMut(&mut Work, i32),
) {
    if w.ig(1) == 0 {
        ddeflt(w, 2);
    }
    w.iset(IV_VNEED, w.ig(IV_VNEED) + w.n);
    let iv1 = w.ig(1);
    if iv1 == 14 || (iv1 > 2 && iv1 < 12) {
        w.g1 = w.ig(IV_G);
    } else {
        w.g1 = 1;
        if iv1 == 12 {
            w.iset(1, 13);
        }
    }
    for _guard in 0..1_000_000 {
        dsumit(w);
        let code = w.ig(1);
        if code == 2 {
            let nf = w.ig(IV_NFGCAL);
            calcg(w, nf);
            continue;
        }
        if code > 2 {
            if code != 14 {
                return;
            }
            let g = w.ig(IV_NEXTV);
            w.iset(IV_G, g);
            w.iset(IV_NEXTV, g + w.n);
            if iv1 != 13 {
                w.g1 = w.ig(IV_G);
                continue;
            }
            return;
        }
        let mut nf = w.ig(IV_NFCALL);
        calcf(w, &mut nf);
        if nf <= 0 {
            w.iset(IV_TOOBIG, 1);
        }
    }
    panic!("dsumsl did not finish, iv(1)={}", w.ig(1));
}

fn dsgrd2(w: &mut Work, alpha: i32, wb: i32) {
    let n = w.n;
    let mut irc = w.ig(IV_SGIRC);
    let mut h = 0.0;
    let mut i = 0i32;
    let mut h0 = 0.0;
    let mut axibar = 0.0;
    let mut alphai = 0.0;
    let mut gi = 0.0;
    let mut label = 0i32;
    if irc < 0 {
        label = 140;
    } else if irc > 0 {
        label = 210;
    }
    loop {
        match label {
            0 => {
                w.sv(wb, 1, d1mach(4));
                w.sv(wb, 2, w.av(wb, 1).sqrt());
                w.sv(wb, 4, w.fx);
                label = 110;
            }
            110 => {
                i = irc.abs() + 1;
                if i > n {
                    label = 300;
                    continue;
                }
                irc = i;
                let afx = w.av(wb, 4).abs();
                let machep = w.av(wb, 1);
                h0 = w.av(wb, 2);
                let hmin = 50.0 * machep;
                w.sv(wb, 6, w.xg(i));
                let axi = w.xg(i).abs();
                axibar = dmax1(axi, 1.0 / w.dg(i));
                gi = w.g(i);
                let agi = gi.abs();
                let eta0 = w.vg(V_ETA0).abs();
                let mut eta = eta0;
                if afx > 0.0 {
                    eta = dmax1(eta, agi * axi * machep / afx);
                }
                alphai = w.av(alpha, i);
                if alphai == 0.0 {
                    label = 170;
                    continue;
                }
                if gi == 0.0 || w.fx == 0.0 {
                    label = 180;
                    continue;
                }
                let afxeta = afx * eta;
                let aai = alphai.abs();
                if gi * gi <= afxeta * aai {
                    h = 2.0 * (afxeta * agi / (aai * aai)).powf(1.0 / 3.0);
                    h *= 1.0 - 2.0 * agi / (3.0 * aai * h + 4.0 * agi);
                } else {
                    h = 2.0 * (afxeta / aai).sqrt();
                    h *= 1.0 - aai * h / (3.0 * aai * h + 4.0 * agi);
                }
                h = dmax1(h, hmin * axibar);
                if aai * h <= 0.002 * agi {
                    label = 160;
                    continue;
                }
                let discon = 2000.0 * afxeta;
                h = discon / (agi + (gi * gi + aai * discon).sqrt());
                h = dmax1(h, hmin * axibar);
                if h >= 0.02 * axibar {
                    h = axibar * h0.powf(2.0 / 3.0);
                }
                irc = -i;
                label = 200;
            }
            140 => {
                h = -w.av(wb, 5);
                i = irc.abs();
                if h > 0.0 {
                    label = 150;
                    continue;
                }
                w.sv(wb, 3, w.fx);
                label = 200;
            }
            150 => {
                let saved = w.av(wb, 6);
                let fh = w.av(wb, 3);
                w.sv(w.g1, i, (fh - w.fx) / (2.0 * h));
                w.xs(i, saved);
                label = 110;
            }
            160 => {
                if h >= 0.02 * axibar {
                    h = h0 * axibar;
                }
                if alphai * gi < 0.0 {
                    h = -h;
                }
                label = 200;
            }
            170 => {
                h = axibar;
                label = 200;
            }
            180 => {
                h = h0 * axibar;
                label = 200;
            }
            200 => {
                let saved = w.av(wb, 6);
                w.xs(i, saved + h);
                w.sv(wb, 5, h);
                w.iset(IV_SGIRC, irc);
                return;
            }
            210 => {
                let gval = (w.fx - w.av(wb, 4)) / w.av(wb, 5);
                w.sv(w.g1, irc, gval);
                w.xs(irc, w.av(wb, 6));
                label = 110;
            }
            300 => {
                w.fx = w.av(wb, 4);
                w.iset(IV_SGIRC, 0);
                return;
            }
            _ => panic!("dsgrd2 label {label}"),
        }
    }
}

fn dsnoit(w: &mut Work) {
    let n = w.n;
    let iv1 = w.ig(1);
    if iv1 == 1 {
        // fall into the dsumit call below
    } else if iv1 == 2 {
        if w.ig(IV_TOOBIG) != 0 {
            w.iset(IV_NFGCAL, 0);
        } else {
            let g1 = w.ig(IV_G);
            let alpha = g1 - n;
            let wb = alpha - 6;
            dsgrd2(w, alpha, wb);
            if w.ig(IV_SGIRC) != 0 {
                w.iset(IV_NGCALL, w.ig(IV_NGCALL) + 1);
                return;
            }
        }
    } else {
        if w.ig(1) == 0 {
            ddeflt(w, 2);
        }
        w.iset(IV_VNEED, w.ig(IV_VNEED) + 2 * n + 6);
        let iv1 = w.ig(1);
        if !(iv1 == 14 || (iv1 > 2 && iv1 < 12)) {
            w.g1 = 1;
            if iv1 == 12 {
                w.iset(1, 13);
            }
        }
    }
    loop {
        if w.ig(1) == 1 || w.ig(1) > 2 {
            if w.ig(1) > 2 && w.ig(1) != 1 {
                // may be the allocation return; handled after dsumit
            }
        }
        let code_before = w.ig(1);
        if code_before == 14 || (code_before > 2 && code_before < 12) {
            w.g1 = w.ig(IV_G);
        }
        dsumit(w);
        let code = w.ig(1);
        if code < 2 {
            return;
        }
        if code > 2 {
            if code != 14 {
                return;
            }
            let g = w.ig(IV_NEXTV) + n + 6;
            w.iset(IV_G, g);
            w.iset(IV_NEXTV, g + n);
            if iv1 != 13 {
                w.g1 = w.ig(IV_G);
                continue;
            }
            return;
        }
        // IV(1) == 2: build a finite-difference gradient.
        if w.ig(IV_NITER) == 0 {
            w.fill_v(n, w.g1, 0.0);
        }
        let mut j = w.ig(IV_LMAT);
        let mut k = w.g1 - n;
        for i in 1..=n {
            let val = w.dotv(i, j, j);
            w.vs(k, val);
            k += 1;
            j += i;
        }
        w.iset(IV_NGCALL, w.ig(IV_NGCALL) - 1);
        w.iset(IV_SGIRC, 0);
        w.fx = w.vg(V_F);
        let g1 = w.ig(IV_G);
        let alpha = g1 - n;
        let wb = alpha - 6;
        dsgrd2(w, alpha, wb);
        if w.ig(IV_SGIRC) == 0 {
            continue;
        }
        w.iset(IV_NGCALL, w.ig(IV_NGCALL) + 1);
        return;
    }
}

pub fn dsmsno(w: &mut Work, mut calcf: impl FnMut(&mut Work, &mut i32)) {
    for _guard in 0..1_000_000 {
        dsnoit(w);
        if w.ig(1) > 2 {
            return;
        }
        let mut nf = w.ig(IV_NFCALL);
        calcf(w, &mut nf);
        if nf <= 0 {
            w.iset(IV_TOOBIG, 1);
        }
    }
    panic!("dsmsno did not finish, iv(1)={}", w.ig(1));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn quadratic_minimum() {
        let n = 2i32;
        let liv = 60i32;
        let lv = 77 + n * (n + 17) / 2;
        let mut w = Work::new(n, &[0.0, 0.0], liv, lv);
        ddeflt(&mut w, 2);
        w.iset(1, 12);
        w.iset(21, 0);
        dsumsl(
            &mut w,
            |w, _nf| {
                let a = w.xg(1) - 3.0;
                let b = w.xg(2) + 1.0;
                w.fx = a * a + b * b;
            },
            |w, _nf| {
                let g1 = w.g1;
                let g0 = 2.0 * (w.xg(1) - 3.0);
                let g1v = 2.0 * (w.xg(2) + 1.0);
                w.sv(g1, 1, g0);
                w.sv(g1, 2, g1v);
            },
        );
        assert!(
            (w.xg(1) - 3.0).abs() < 1e-8 && (w.xg(2) + 1.0).abs() < 1e-8,
            "x=({}, {}), f={}, iv1={}",
            w.xg(1),
            w.xg(2),
            w.vg(V_F),
            w.ig(1)
        );
    }

    #[test]
    fn quadratic_three() {
        let n = 3i32;
        let liv = 60i32;
        let lv = 77 + n * (n + 17) / 2;
        let mut w = Work::new(n, &[0.0, 0.0, 0.0], liv, lv);
        ddeflt(&mut w, 2);
        w.iset(1, 12);
        w.iset(21, 0);
        let target = [1.0, -2.0, 0.5];
        dsumsl(
            &mut w,
            |w, _nf| {
                let mut s = 0.0;
                for i in 1..=3 {
                    let d = w.xg(i) - target[(i as usize) - 1];
                    s += d * d;
                }
                w.fx = s;
            },
            |w, _nf| {
                let g1 = w.g1;
                for i in 1..=3 {
                    w.sv(g1, i, 2.0 * (w.xg(i) - target[(i as usize) - 1]));
                }
            },
        );
        for i in 1..=3 {
            let err = (w.xg(i) - target[(i as usize) - 1]).abs();
            assert!(err < 1e-8, "i={i} x={} iv1={}", w.xg(i), w.ig(1));
        }
    }
}
