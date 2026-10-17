//! Classification-tree builder from randomForest `src/rfsub.f`.
//!
//! `buildtree`, `findbestsplit`, and `movedata` follow the Fortran, including
//! default-real literals (`1.0e-5`, `1.0 / ntie`) which are single precision
//! before they are compared with double precision draws. `catmax`, `catmaxb`,
//! `unpack`, and `rrand` are the C routines that file calls. `rrand` is R's
//! `unif_rand`, supplied by the caller so the stream stays outside this crate.
//! Categorical two-class splits use the same Singleton quicksort as `R_qsort_I`.

use std::sync::atomic::{AtomicUsize, Ordering};

static UNIF: AtomicUsize = AtomicUsize::new(0);

#[no_mangle]
pub extern "C" fn rfsub_set_unif(draw: extern "C" fn() -> f64) {
    UNIF.store(draw as usize, Ordering::SeqCst);
}

fn rrand() -> f64 {
    let address = UNIF.load(Ordering::SeqCst);
    if address == 0 {
        panic!("rfsub_set_unif was not called");
    }
    let draw: extern "C" fn() -> f64 = unsafe { std::mem::transmute(address) };
    draw()
}

fn real4(value: f32) -> f64 {
    value as f64
}

fn one_over_tie(ntie: i32) -> f64 {
    (1.0f32 / (ntie as f32)) as f64
}

fn a_index(mdim: usize, row: i32, col: i32) -> usize {
    (col as usize - 1) * mdim + (row as usize - 1)
}

fn ld_index(leading: usize, row: i32, col: i32) -> usize {
    (col as usize - 1) * leading + (row as usize - 1)
}

/// `R_qsort_I`. `left` and `right` are 1-based inclusive positions.
pub fn qsort_i(values: &mut [f64], index: &mut [i32], mut left: i32, mut right: i32) {
    let mut lower = [0i32; 40];
    let mut upper = [0i32; 40];
    let mut ratio = 0.375f64;
    let origin = left;
    let mut depth = 1i32;
    let mut step = 0i32;
    loop {
        if step == 0 {
            if left < right {
                if ratio < 0.5898437 {
                    ratio += 0.0390625;
                } else {
                    ratio -= 0.21875;
                }
                step = 1;
                continue;
            }
            step = 2;
            continue;
        }
        if step == 1 {
            let mut cursor = left;
            let pivot_at = left + ((right - left) as f64 * ratio) as i32;
            let mut pivot_index = index[pivot_at as usize - 1];
            let mut pivot = values[pivot_at as usize - 1];
            if values[left as usize - 1] > pivot {
                index[pivot_at as usize - 1] = index[left as usize - 1];
                index[left as usize - 1] = pivot_index;
                pivot_index = index[pivot_at as usize - 1];
                values[pivot_at as usize - 1] = values[left as usize - 1];
                values[left as usize - 1] = pivot;
                pivot = values[pivot_at as usize - 1];
            }
            let mut scan = right;
            if values[right as usize - 1] < pivot {
                index[pivot_at as usize - 1] = index[right as usize - 1];
                index[right as usize - 1] = pivot_index;
                pivot_index = index[pivot_at as usize - 1];
                values[pivot_at as usize - 1] = values[right as usize - 1];
                values[right as usize - 1] = pivot;
                pivot = values[pivot_at as usize - 1];
                if values[left as usize - 1] > pivot {
                    index[pivot_at as usize - 1] = index[left as usize - 1];
                    index[left as usize - 1] = pivot_index;
                    pivot_index = index[pivot_at as usize - 1];
                    values[pivot_at as usize - 1] = values[left as usize - 1];
                    values[left as usize - 1] = pivot;
                    pivot = values[pivot_at as usize - 1];
                }
            }
            loop {
                scan -= 1;
                while values[scan as usize - 1] > pivot {
                    scan -= 1;
                }
                let held_index = index[scan as usize - 1];
                let held = values[scan as usize - 1];
                cursor += 1;
                while values[cursor as usize - 1] < pivot {
                    cursor += 1;
                }
                if cursor > scan {
                    break;
                }
                index[scan as usize - 1] = index[cursor as usize - 1];
                index[cursor as usize - 1] = held_index;
                values[scan as usize - 1] = values[cursor as usize - 1];
                values[cursor as usize - 1] = held;
            }
            depth += 1;
            if scan - left <= right - cursor {
                lower[depth as usize] = cursor;
                upper[depth as usize] = right;
                right = scan;
            } else {
                lower[depth as usize] = left;
                upper[depth as usize] = scan;
                left = cursor;
            }
            step = 3;
            continue;
        }
        if step == 2 {
            if depth == 1 {
                return;
            }
            left = lower[depth as usize];
            right = upper[depth as usize];
            depth -= 1;
            step = 3;
            continue;
        }
        if step == 3 {
            if right - left > 10 {
                step = 1;
                continue;
            }
            if left == origin {
                step = 0;
                continue;
            }
            left -= 1;
            step = 4;
            continue;
        }
        loop {
            left += 1;
            if left == right {
                step = 2;
                break;
            }
            let pivot_index = index[left as usize];
            let pivot = values[left as usize];
            if values[left as usize - 1] <= pivot {
                continue;
            }
            let mut cursor = left;
            loop {
                index[cursor as usize] = index[cursor as usize - 1];
                values[cursor as usize] = values[cursor as usize - 1];
                cursor -= 1;
                if !(pivot < values[cursor as usize - 1]) {
                    break;
                }
            }
            index[cursor as usize] = pivot_index;
            values[cursor as usize] = pivot;
        }
    }
}

fn pack(n_bits: i32, bits: &[i32]) -> f64 {
    let mut i = n_bits - 1;
    let mut packed = bits[i as usize] as f64;
    while i > 0 {
        i -= 1;
        packed = 2.0 * packed + bits[i as usize] as f64;
    }
    packed
}

fn unpack(packed: f64, n_bits: i32, bits: &mut [i32]) {
    let mut x = packed;
    for i in 0..=n_bits as usize {
        bits[i] = if (x as u64) & 1 == 1 { 1 } else { 0 };
        x /= 2.0;
    }
}

fn catmax(
    parent_den: f64,
    tclasscat: &[f64],
    tclasspop: &[f64],
    nclass: i32,
    lcat: i32,
    critmax: &mut f64,
    maxcat: i32,
    ncmax: i32,
    ncsplit: i32,
) -> (f64, i32) {
    let _ = maxcat;
    let nclass_u = nclass as usize;
    let mut icat = [0i32; 54];
    let mut left_count = vec![0.0f64; nclass_u];
    let mut nhit = 0i32;
    let mut best = 0.0f64;
    let nsplit = if lcat > ncmax {
        ncsplit
    } else {
        (2.0f64.powi(lcat - 1) as i32) - 1
    };
    for n in 0..nsplit {
        icat.fill(0);
        if lcat > ncmax {
            for j in 0..lcat as usize {
                icat[j] = if rrand() > 0.5 { 1 } else { 0 };
            }
        } else {
            unpack((n + 1) as f64, lcat, &mut icat);
        }
        for j in 0..nclass_u {
            left_count[j] = 0.0;
            for k in 0..lcat as usize {
                if icat[k] != 0 {
                    left_count[j] += tclasscat[j + k * nclass_u];
                }
            }
        }
        let mut left_num = 0.0;
        let mut left_den = 0.0;
        for j in 0..nclass_u {
            left_num += left_count[j] * left_count[j];
            left_den += left_count[j];
        }
        if left_den <= 1.0e-8 || parent_den - left_den <= 1.0e-5 {
            continue;
        }
        let mut right_num = 0.0;
        for j in 0..nclass_u {
            left_count[j] = tclasspop[j] - left_count[j];
            right_num += left_count[j] * left_count[j];
        }
        let dec_gini = (left_num / left_den) + (right_num / (parent_den - left_den));
        if dec_gini > *critmax {
            *critmax = dec_gini;
            nhit = 1;
            best = if lcat > ncmax {
                pack(lcat, &icat)
            } else {
                (n + 1) as f64
            };
        }
    }
    (best, nhit)
}

fn catmaxb(
    total_wt: f64,
    tclasscat: &[f64],
    class_count: &[f64],
    nclass: i32,
    n_cat: i32,
    critmax: &mut f64,
    cat_count: &[f64],
) -> (f64, i32) {
    let nclass_u = nclass as usize;
    let n_cat_u = n_cat as usize;
    let mut cat_proportion = [0.0f64; 53];
    let mut cp = [0.0f64; 53];
    let mut cm = [0.0f64; 53];
    let mut kcat = [0i32; 53];
    let mut nhit = 0i32;
    let mut bestsplit = 0.0f64;
    for i in 0..n_cat_u {
        cat_proportion[i] = if cat_count[i] != 0.0 {
            tclasscat[i * nclass_u] / cat_count[i]
        } else {
            0.0
        };
        kcat[i] = (i as i32) + 1;
    }
    qsort_i(
        &mut cat_proportion[..],
        &mut kcat[..],
        1,
        n_cat,
    );
    for i in 0..nclass_u {
        cp[i] = 0.0;
        cm[i] = class_count[i];
    }
    let mut right_den = total_wt;
    let mut left_den = 0.0;
    for i in 0..(n_cat_u - 1) {
        let category = kcat[i] - 1;
        left_den += cat_count[category as usize];
        right_den -= cat_count[category as usize];
        let mut left_num = 0.0;
        let mut right_num = 0.0;
        for j in 0..nclass_u {
            let amount = tclasscat[j + (category as usize) * nclass_u];
            cp[j] += amount;
            cm[j] -= amount;
            left_num += cp[j] * cp[j];
            right_num += cm[j] * cm[j];
        }
        if cat_proportion[i] < cat_proportion[i + 1] && right_den > 1.0e-5 && left_den > 1.0e-5 {
            let crit = (left_num / left_den) + (right_num / right_den);
            if crit > *critmax {
                *critmax = crit;
                bestsplit = 0.5 * (cat_proportion[i] + cat_proportion[i + 1]);
                nhit = 1;
            }
        }
    }
    let best = if nhit == 1 {
        for i in 0..n_cat_u {
            cat_proportion[i] = if cat_count[i] != 0.0 {
                tclasscat[i * nclass_u] / cat_count[i]
            } else {
                0.0
            };
            kcat[i] = if cat_proportion[i] < bestsplit { 1 } else { 0 };
        }
        pack(n_cat, &kcat)
    } else {
        0.0
    };
    (best, nhit)
}

struct SplitOut {
    msplit: i32,
    decsplit: f64,
    best: f64,
    jstat: i32,
}

fn findbestsplit(
    a: &[i32],
    b: &[i32],
    cl: &[i32],
    mdim: usize,
    nsample: usize,
    nclass: usize,
    cat: &[i32],
    maxcat: i32,
    ndstart: i32,
    ndend: i32,
    tclasspop: &[f64],
    tclasscat: &mut [f64],
    ncase: &[i32],
    mtry: i32,
    win: &[f64],
    wr: &mut [f64],
    wl: &mut [f64],
    mred: usize,
    mind: &mut [i32],
) -> SplitOut {
    let ncmax = 10i32;
    let ncsplit = 512i32;
    let mut pno = 0.0;
    let mut pdo = 0.0;
    for j in 0..nclass {
        pno += tclasspop[j] * tclasspop[j];
        pdo += tclasspop[j];
    }
    let crit0 = pno / pdo;
    let mut jstat = 0i32;
    let mut critmax = real4(-1.0e25);
    for k in 0..mred {
        mind[k] = (k as i32) + 1;
    }
    let mut nn = mred as i32;
    let mut msplit = 0i32;
    let mut best = 0.0f64;
    let gap = real4(1.0e-5);
    for _mt in 1..=mtry {
        let xrand = rrand();
        let j = (nn as f64 * xrand) as i32 + 1;
        let mvar = mind[j as usize - 1];
        mind[j as usize - 1] = mind[nn as usize - 1];
        mind[nn as usize - 1] = mvar;
        nn -= 1;
        let lcat = cat[mvar as usize - 1];
        if lcat == 1 {
            let mut rrn = pno;
            let mut rrd = pdo;
            let mut rln = 0.0;
            let mut rld = 0.0;
            wl.fill(0.0);
            wr[..nclass].copy_from_slice(&tclasspop[..nclass]);
            let mut ntie = 1i32;
            let mut nsp = ndstart;
            while nsp <= ndend - 1 {
                let nc = a[a_index(mdim, mvar, nsp)];
                let u = win[nc as usize - 1];
                let k = cl[nc as usize - 1];
                let k0 = k as usize - 1;
                rln += u * (2.0 * wl[k0] + u);
                rrn += u * (-2.0 * wr[k0] + u);
                rld += u;
                rrd -= u;
                wl[k0] += u;
                wr[k0] -= u;
                let next_case = a[a_index(mdim, mvar, nsp + 1)];
                let rank_here = b[a_index(mdim, mvar, nc)];
                let rank_next = b[a_index(mdim, mvar, next_case)];
                if rank_here < rank_next && rrd.min(rld) > gap {
                    let crit = (rln / rld) + (rrn / rrd);
                    if crit > critmax {
                        best = nsp as f64;
                        critmax = crit;
                        msplit = mvar;
                        ntie = 1;
                    }
                    if crit == critmax {
                        ntie += 1;
                        if rrand() < one_over_tie(ntie) {
                            best = nsp as f64;
                            critmax = crit;
                            msplit = mvar;
                        }
                    }
                }
                nsp += 1;
            }
        } else {
            for item in tclasscat.iter_mut() {
                *item = 0.0;
            }
            let mut nsp = ndstart;
            while nsp <= ndend {
                let nc = ncase[nsp as usize - 1];
                let l = a[a_index(mdim, mvar, nc)];
                let class = cl[nc as usize - 1];
                let slot = ld_index(nclass, class, l);
                tclasscat[slot] += win[nc as usize - 1];
                nsp += 1;
            }
            let mut dn = [0.0f64; 53];
            let mut nnz = 0i32;
            for i in 1..=lcat {
                let mut su = 0.0;
                for j in 1..=nclass as i32 {
                    su += tclasscat[ld_index(nclass, j, i)];
                }
                dn[(i as usize) - 1] = su;
                if su > 0.0 {
                    nnz += 1;
                }
            }
            let mut nhit = 0i32;
            if nnz > 1 {
                if nclass == 2 && lcat > ncmax {
                    let (split, hit) = catmaxb(
                        pdo,
                        tclasscat,
                        tclasspop,
                        nclass as i32,
                        lcat,
                        &mut critmax,
                        &dn,
                    );
                    nhit = hit;
                    if hit == 1 {
                        best = split;
                    }
                } else {
                    let (split, hit) = catmax(
                        pdo,
                        tclasscat,
                        tclasspop,
                        nclass as i32,
                        lcat,
                        &mut critmax,
                        maxcat,
                        ncmax,
                        ncsplit,
                    );
                    nhit = hit;
                    if hit == 1 {
                        best = split;
                    }
                }
                if nhit == 1 {
                    msplit = mvar;
                }
            }
        }
    }
    if critmax < real4(-1.0e10) || msplit == 0 {
        jstat = -1;
    }
    SplitOut {
        msplit,
        decsplit: critmax - crit0,
        best,
        jstat,
    }
}

fn movedata(
    a: &mut [i32],
    ta: &mut [i32],
    mdim: usize,
    ndstart: i32,
    ndend: i32,
    idmove: &mut [i32],
    ncase: &mut [i32],
    msplit: i32,
    cat: &[i32],
    best: f64,
) -> i32 {
    let mut ndendl;
    if cat[msplit as usize - 1] == 1 {
        let stop = best as i32;
        let mut nsp = ndstart;
        while nsp <= stop {
            let nc = a[a_index(mdim, msplit, nsp)];
            idmove[nc as usize - 1] = 1;
            nsp += 1;
        }
        nsp = stop + 1;
        while nsp <= ndend {
            let nc = a[a_index(mdim, msplit, nsp)];
            idmove[nc as usize - 1] = 0;
            nsp += 1;
        }
        ndendl = stop;
    } else {
        ndendl = ndstart - 1;
        let l = cat[msplit as usize - 1];
        let mut icat = [0i32; 54];
        unpack(best, l, &mut icat);
        let mut nsp = ndstart;
        while nsp <= ndend {
            let nc = ncase[nsp as usize - 1];
            let category = a[a_index(mdim, msplit, nc)];
            if icat[category as usize - 1] == 1 {
                idmove[nc as usize - 1] = 1;
                ndendl += 1;
            } else {
                idmove[nc as usize - 1] = 0;
            }
            nsp += 1;
        }
    }
    for msh in 1..=mdim as i32 {
        if cat[msh as usize - 1] == 1 {
            let mut k = ndstart - 1;
            let mut n = ndstart;
            while n <= ndend {
                let ih = a[a_index(mdim, msh, n)];
                if idmove[ih as usize - 1] == 1 {
                    k += 1;
                    ta[k as usize - 1] = a[a_index(mdim, msh, n)];
                }
                n += 1;
            }
            n = ndstart;
            while n <= ndend {
                let ih = a[a_index(mdim, msh, n)];
                if idmove[ih as usize - 1] == 0 {
                    k += 1;
                    ta[k as usize - 1] = a[a_index(mdim, msh, n)];
                }
                n += 1;
            }
            let mut kk = ndstart;
            while kk <= ndend {
                a[a_index(mdim, msh, kk)] = ta[kk as usize - 1];
                kk += 1;
            }
        }
    }
    if cat[msplit as usize - 1] == 1 {
        let mut n = ndstart;
        while n <= ndend {
            ncase[n as usize - 1] = a[a_index(mdim, msplit, n)];
            n += 1;
        }
    } else {
        let mut k = ndstart - 1;
        let mut n = ndstart;
        while n <= ndend {
            if idmove[ncase[n as usize - 1] as usize - 1] == 1 {
                k += 1;
                ta[k as usize - 1] = ncase[n as usize - 1];
            }
            n += 1;
        }
        n = ndstart;
        while n <= ndend {
            if idmove[ncase[n as usize - 1] as usize - 1] == 0 {
                k += 1;
                ta[k as usize - 1] = ncase[n as usize - 1];
            }
            n += 1;
        }
        let mut kk = ndstart;
        while kk <= ndend {
            ncase[kk as usize - 1] = ta[kk as usize - 1];
            kk += 1;
        }
    }
    ndendl
}

#[no_mangle]
pub extern "C" fn rfsub_buildtree(
    a: *mut i32,
    b: *mut i32,
    cl: *mut i32,
    cat: *mut i32,
    maxcat: i32,
    mdim: i32,
    nsample: i32,
    nclass: i32,
    treemap: *mut i32,
    bestvar: *mut i32,
    bestsplit: *mut f64,
    bestsplitnext: *mut f64,
    tgini: *mut f64,
    nodestatus: *mut i32,
    nodepop: *mut i32,
    nodestart: *mut i32,
    classpop: *mut f64,
    tclasspop: *mut f64,
    tclasscat: *mut f64,
    ta: *mut i32,
    nrnodes: i32,
    idmove: *mut i32,
    ndsize: i32,
    ncase: *mut i32,
    mtry: i32,
    iv: *mut i32,
    nodeclass: *mut i32,
    ndbigtree: *mut i32,
    win: *mut f64,
    wr: *mut f64,
    wl: *mut f64,
    mred: i32,
    nuse: i32,
    mind: *mut i32,
) {
    let mdim_u = mdim as usize;
    let nsample_u = nsample as usize;
    let nclass_u = nclass as usize;
    let nr_u = nrnodes as usize;
    let mred_u = mred as usize;
    unsafe {
        let a = std::slice::from_raw_parts_mut(a, mdim_u * nsample_u);
        let b = std::slice::from_raw_parts_mut(b, mdim_u * nsample_u);
        let cl = std::slice::from_raw_parts(cl, nsample_u);
        let cat = std::slice::from_raw_parts(cat, mdim_u);
        let treemap = std::slice::from_raw_parts_mut(treemap, 2 * nr_u);
        let bestvar = std::slice::from_raw_parts_mut(bestvar, nr_u);
        let bestsplit = std::slice::from_raw_parts_mut(bestsplit, nr_u);
        let bestsplitnext = std::slice::from_raw_parts_mut(bestsplitnext, nr_u);
        let tgini = std::slice::from_raw_parts_mut(tgini, mdim_u);
        let nodestatus = std::slice::from_raw_parts_mut(nodestatus, nr_u);
        let nodepop = std::slice::from_raw_parts_mut(nodepop, nr_u);
        let nodestart = std::slice::from_raw_parts_mut(nodestart, nr_u);
        let classpop = std::slice::from_raw_parts_mut(classpop, nclass_u * nr_u);
        let tclasspop = std::slice::from_raw_parts_mut(tclasspop, nclass_u);
        let tclasscat = std::slice::from_raw_parts_mut(tclasscat, nclass_u * 53);
        let ta = std::slice::from_raw_parts_mut(ta, nsample_u);
        let idmove = std::slice::from_raw_parts_mut(idmove, nsample_u);
        let ncase = std::slice::from_raw_parts_mut(ncase, nsample_u);
        let iv = std::slice::from_raw_parts_mut(iv, mred_u);
        let nodeclass = std::slice::from_raw_parts_mut(nodeclass, nr_u);
        let win = std::slice::from_raw_parts(win, nsample_u);
        let wr = std::slice::from_raw_parts_mut(wr, nclass_u);
        let wl = std::slice::from_raw_parts_mut(wl, nclass_u);
        let mind = std::slice::from_raw_parts_mut(mind, mred_u);

        nodestatus.fill(0);
        nodestart.fill(0);
        nodepop.fill(0);
        classpop.fill(0.0);
        for j in 1..=nclass {
            classpop[ld_index(nclass_u, j, 1)] = tclasspop[j as usize - 1];
        }
        let mut ncur = 1i32;
        nodestart[0] = 1;
        nodepop[0] = nuse;
        nodestatus[0] = 2;
        let mut msplit_keep = 0i32;
        for kbuild in 1..=nrnodes {
            if kbuild > ncur {
                break;
            }
            if nodestatus[kbuild as usize - 1] != 2 {
                continue;
            }
            let ndstart = nodestart[kbuild as usize - 1];
            let ndend = ndstart + nodepop[kbuild as usize - 1] - 1;
            for j in 1..=nclass {
                tclasspop[j as usize - 1] = classpop[ld_index(nclass_u, j, kbuild)];
            }
            let split = findbestsplit(
                a,
                b,
                cl,
                mdim_u,
                nsample_u,
                nclass_u,
                cat,
                maxcat,
                ndstart,
                ndend,
                tclasspop,
                tclasscat,
                ncase,
                mtry,
                win,
                wr,
                wl,
                mred_u,
                mind,
            );
            msplit_keep = split.msplit;
            if split.jstat == -1 {
                nodestatus[kbuild as usize - 1] = -1;
                continue;
            }
            bestvar[kbuild as usize - 1] = split.msplit;
            iv[split.msplit as usize - 1] = 1;
            let mut decsplit = split.decsplit;
            if decsplit < 0.0 {
                decsplit = 0.0;
            }
            tgini[split.msplit as usize - 1] += decsplit;
            if cat[split.msplit as usize - 1] == 1 {
                let at = split.best as i32;
                bestsplit[kbuild as usize - 1] =
                    a[a_index(mdim_u, split.msplit, at)] as f64;
                bestsplitnext[kbuild as usize - 1] =
                    a[a_index(mdim_u, split.msplit, at + 1)] as f64;
            } else {
                bestsplit[kbuild as usize - 1] = split.best;
                bestsplitnext[kbuild as usize - 1] = 0.0;
            }
            let ndendl = movedata(
                a,
                ta,
                mdim_u,
                ndstart,
                ndend,
                idmove,
                ncase,
                split.msplit,
                cat,
                split.best,
            );
            nodepop[(ncur + 1) as usize - 1] = ndendl - ndstart + 1;
            nodepop[(ncur + 2) as usize - 1] = ndend - ndendl;
            nodestart[(ncur + 1) as usize - 1] = ndstart;
            nodestart[(ncur + 2) as usize - 1] = ndendl + 1;
            let mut n = ndstart;
            while n <= ndendl {
                let nc = ncase[n as usize - 1];
                let j = cl[nc as usize - 1];
                classpop[ld_index(nclass_u, j, ncur + 1)] += win[nc as usize - 1];
                n += 1;
            }
            n = ndendl + 1;
            while n <= ndend {
                let nc = ncase[n as usize - 1];
                let j = cl[nc as usize - 1];
                classpop[ld_index(nclass_u, j, ncur + 2)] += win[nc as usize - 1];
                n += 1;
            }
            nodestatus[(ncur + 1) as usize - 1] = 2;
            nodestatus[(ncur + 2) as usize - 1] = 2;
            if nodepop[(ncur + 1) as usize - 1] <= ndsize {
                nodestatus[(ncur + 1) as usize - 1] = -1;
            }
            if nodepop[(ncur + 2) as usize - 1] <= ndsize {
                nodestatus[(ncur + 2) as usize - 1] = -1;
            }
            let mut popt1 = 0.0;
            let mut popt2 = 0.0;
            for j in 1..=nclass {
                popt1 += classpop[ld_index(nclass_u, j, ncur + 1)];
                popt2 += classpop[ld_index(nclass_u, j, ncur + 2)];
            }
            for j in 1..=nclass {
                if classpop[ld_index(nclass_u, j, ncur + 1)] == popt1 {
                    nodestatus[(ncur + 1) as usize - 1] = -1;
                }
                if classpop[ld_index(nclass_u, j, ncur + 2)] == popt2 {
                    nodestatus[(ncur + 2) as usize - 1] = -1;
                }
            }
            treemap[ld_index(2, 1, kbuild)] = ncur + 1;
            treemap[ld_index(2, 2, kbuild)] = ncur + 2;
            nodestatus[kbuild as usize - 1] = 1;
            ncur += 2;
            if ncur >= nrnodes {
                break;
            }
        }
        let _ = msplit_keep;
        let mut big = nrnodes;
        for k in (1..=nrnodes).rev() {
            if nodestatus[k as usize - 1] == 0 {
                big -= 1;
            }
            if nodestatus[k as usize - 1] == 2 {
                nodestatus[k as usize - 1] = -1;
            }
        }
        *ndbigtree = big;
        for kn in 1..=big {
            if nodestatus[kn as usize - 1] == -1 {
                let mut pp = 0.0;
                let mut ntie = 1i32;
                for j in 1..=nclass {
                    let pop = classpop[ld_index(nclass_u, j, kn)];
                    if pop > pp {
                        nodeclass[kn as usize - 1] = j;
                        pp = pop;
                        ntie = 1;
                    }
                    if pop == pp {
                        ntie += 1;
                        if rrand() < one_over_tie(ntie) {
                            nodeclass[kn as usize - 1] = j;
                            pp = pop;
                        }
                    }
                }
            }
        }
    }
}

#[no_mangle]
pub extern "C" fn rfsub_qsort_i(values: *mut f64, index: *mut i32, n: i32, left: i32, right: i32) {
    unsafe {
        let values = std::slice::from_raw_parts_mut(values, n as usize);
        let index = std::slice::from_raw_parts_mut(index, n as usize);
        qsort_i(values, index, left, right);
    }
}
