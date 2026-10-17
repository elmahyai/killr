//! Myers shortest edit script, ported from diffobj `src/diff.c`.
//!
//! The C routine is the Hirschberg linear-space form of Myers' algorithm,
//! with the fixed buffers and the `max.diffs` failover added in diffobj.
//! Comparison is string equality, which is what `enc2utf8` plus R's CHARSXP
//! cache does. Offsets in the edit list are 0-based. `diffs` is negative when
//! the difference limit was hit. A negative `max_diffs` means no limit, the
//! same as passing `-1L` into the C entry point.

const INT_MAX: i32 = i32::MAX;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Op {
    Null = 0,
    Match = 1,
    Delete = 2,
    Insert = 3,
}

impl Op {
    /// Codes stored by `DIFFOBJ_diffobj`: Match 1, Insert 2, Delete 3.
    fn r_code(self) -> i32 {
        match self {
            Op::Match => 1,
            Op::Insert => 2,
            Op::Delete => 3,
            Op::Null => 0,
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct Edit {
    op: Op,
    off: i32,
    len: i32,
}

struct Ctx {
    buf: Vec<i32>,
    bufmax: i32,
    ses: Vec<Edit>,
    si: i32,
    simax: i32,
    dmax: i32,
    dmaxhit: i32,
}

struct Middle {
    x: i32,
    y: i32,
    u: i32,
    v: i32,
}

/// One edit, already mapped to the R type codes.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MbaEdit {
    /// 1 match, 2 insert, 3 delete.
    pub kind: i32,
    pub len: i32,
    pub off: i32,
}

/// Shortest edit script for two sequences.
///
/// `max_diffs` below zero disables the limit. The second value is the
/// difference count, negative when the limit stopped the search.
pub fn myers_diff(a: &[&str], b: &[&str], max_diffs: i32) -> Result<(Vec<MbaEdit>, i32), String> {
    let n = i32::try_from(a.len()).map_err(|_| length_error())?;
    let m = i32::try_from(b.len()).map_err(|_| length_error())?;
    let max_i = if max_diffs < 0 { -1 } else { max_diffs };
    let (edits, d) = diff(a, 0, n, b, 0, m, max_i)?;
    Ok((edits, d))
}

fn length_error() -> String {
    format!("Combined length of diffed vectors exeeds INT_MAX ({INT_MAX})")
}

fn diff(
    a: &[&str],
    aoff: i32,
    n: i32,
    b: &[&str],
    boff: i32,
    m: i32,
    dmax: i32,
) -> Result<(Vec<MbaEdit>, i32), String> {
    if n < 0 || m < 0 {
        return Err("Logic Error: negative lengths; contact maintainer.".into());
    }
    if n > INT_MAX - m {
        return Err(length_error());
    }
    let mut delta = n - m;
    if delta < 0 {
        delta = -delta;
    }
    if n + m > INT_MAX - delta {
        return Err("Logic Error: exceeded max allowable combined string length.".into());
    }
    if n + m + delta > INT_MAX / 4 - 1 {
        return Err("Logic Error: exceeded max allowable combined string length.".into());
    }
    let bufmax = 4 * (n + m + delta) + 1;
    let mut ctx = Ctx {
        buf: vec![0; bufmax as usize],
        bufmax,
        ses: vec![
            Edit {
                op: Op::Null,
                off: 0,
                len: 0,
            };
            (n + m + 1) as usize
        ],
        si: 0,
        simax: n + m,
        dmax: if dmax >= 0 { dmax } else { INT_MAX },
        dmaxhit: 0,
    };

    if boff > INT_MAX - m || aoff > INT_MAX - n {
        return Err("Internal error: overflow for a/boff; contact maintainer".into());
    }

    let mut x = 0;
    let mut y = 0;
    while x < n && y < m {
        if !comp(a, aoff + x, b, boff + y)? {
            break;
        }
        x += 1;
        y += 1;
    }
    edit(&mut ctx, Op::Match, aoff, x)?;
    let d = ses(a, aoff + x, n - x, b, boff + y, m - y, &mut ctx)?;
    let sn = if ctx.ses[0].op != Op::Null {
        ctx.si + 1
    } else {
        0
    };
    let edits = ctx.ses[..sn as usize]
        .iter()
        .map(|item| MbaEdit {
            kind: item.op.r_code(),
            len: item.len,
            off: item.off,
        })
        .collect();
    let signed = d * if ctx.dmaxhit != 0 { -1 } else { 1 };
    Ok((edits, signed))
}

fn comp(a: &[&str], aidx: i32, b: &[&str], bidx: i32) -> Result<bool, String> {
    let alen = a.len() as i32;
    let blen = b.len() as i32;
    if aidx >= alen && bidx >= blen {
        return Err(
            "Internal Error: reached theoretically unreachable branch 1, contact maintainer."
                .into(),
        );
    }
    if aidx >= alen || bidx >= blen {
        return Ok(false);
    }
    Ok(a[aidx as usize] == b[bidx as usize])
}

fn setv(ctx: &mut Ctx, k: i32, r: i32, val: i32) -> Result<(), String> {
    let j = index_of(k, r);
    if j > ctx.bufmax || j < 0 {
        return Err(format!(
            "Logic Error: exceeded buffer size ({j} vs {}); contact maintainer.",
            ctx.bufmax
        ));
    }
    ctx.buf[j as usize] = val;
    Ok(())
}

fn v(ctx: &Ctx, k: i32, r: i32) -> Result<i32, String> {
    let j = index_of(k, r);
    if j > ctx.bufmax || j < 0 {
        return Err(format!(
            "Logic Error: exceeded buffer 2 size ({j} vs {}); contact maintainer.",
            ctx.bufmax
        ));
    }
    Ok(ctx.buf[j as usize])
}

fn index_of(k: i32, r: i32) -> i32 {
    if k <= 0 {
        k.wrapping_neg().wrapping_mul(4).wrapping_add(r)
    } else {
        k.wrapping_mul(4).wrapping_add(r.wrapping_sub(2))
    }
}

/// Squared distance the way the C file computes it: the product is a 32-bit
/// int, then that bit pattern is converted to double.
fn dist2(x0: i32, y0: i32, x1: i32, y1: i32) -> f64 {
    let dx = x0.wrapping_sub(x1);
    let dy = y0.wrapping_sub(y1);
    f64::from(dx.wrapping_mul(dx)) + f64::from(dy.wrapping_mul(dy))
}

fn find_faux_snake(
    a: &[&str],
    aoff: i32,
    n: i32,
    b: &[&str],
    boff: i32,
    m: i32,
    ms: &mut Middle,
    d: i32,
) -> Result<(i32, Vec<Op>), String> {
    let mut x = ms.x;
    let mut y = ms.y;
    if x < 0 || y < 0 || ms.u < 0 || ms.v < 0 {
        return Err("Internal Error: fake snake with -ve start; contact maintainer.".into());
    }
    let mut steps = 0i32;
    let mut diffs = 0i32;
    let mut step_dir = 1i32;
    if x > ms.u || y > ms.v {
        ms.u = n;
        ms.v = m;
        diffs -= d;
        if x > ms.u || y > ms.v {
            return Err(
                "Internal Error: can't correct fwd snake overshoot; contact maintainer".into(),
            );
        }
    }
    if ms.u > INT_MAX - ms.v - 1 {
        return Err("Logic Error: fake snake step overflow? Contact maintainer.".into());
    }
    let max_steps = (ms.u - x) + (ms.v - y) + 1;
    let mut faux = vec![Op::Null; max_steps as usize];
    while x < ms.u || y < ms.v {
        if x < ms.u && y < ms.v && comp(a, aoff + x, b, boff + y)? {
            x += 1;
            y += 1;
            faux[steps as usize] = Op::Match;
        } else if x < ms.u && (step_dir != 0 || y >= ms.v) {
            x += 1;
            diffs += 1;
            step_dir = if step_dir == 0 { 1 } else { 0 };
            faux[steps as usize] = Op::Delete;
        } else if y < ms.v && (step_dir == 0 || x >= ms.u) {
            y += 1;
            diffs += 1;
            faux[steps as usize] = Op::Insert;
            step_dir = if step_dir == 0 { 1 } else { 0 };
        } else {
            return Err(
                "Logic Error: unexpected outcome in snake creation process; contact maintainer"
                    .into(),
            );
        }
        steps += 1;
    }
    if x != ms.u || y != ms.v || steps >= max_steps {
        return Err("Logic Error: faux snake process failed; contact maintainer.".into());
    }
    faux.truncate(steps as usize);
    Ok((diffs, faux))
}

fn find_middle_snake(
    a: &[&str],
    aoff: i32,
    n: i32,
    b: &[&str],
    boff: i32,
    m: i32,
    ctx: &mut Ctx,
    ms: &mut Middle,
) -> Result<(i32, Option<Vec<Op>>), String> {
    ms.x = 0;
    ms.y = 0;
    ms.u = n;
    ms.v = m;
    let mut x_max = 0;
    let mut y_max = 0;
    let mut u_max = n;
    let mut v_max = m;
    let mut dist = dist2(x_max, y_max, u_max, v_max);
    let delta = n - m;
    let odd = delta & 1;
    let mut mid = (n + m) / 2;
    mid += odd;

    setv(ctx, 1, 0, 0)?;
    setv(ctx, delta - 1, 1, n)?;

    for d in 0..=mid {
        if 2 * (d - 1) > ctx.dmax - 1 {
            ctx.dmaxhit = 1;
            ms.x = x_max;
            ms.y = y_max;
            ms.u = u_max;
            ms.v = v_max;
            let (extra, faux) = find_faux_snake(a, aoff, n, b, boff, m, ms, d - 1)?;
            let used = if faux.first().copied().unwrap_or(Op::Null) == Op::Null {
                None
            } else {
                Some(faux)
            };
            return Ok((2 * (d - 1) + extra, used));
        }

        let mut k = d;
        while k >= -d {
            let x_pick = if k == -d || (k != d && v(ctx, k - 1, 0)? < v(ctx, k + 1, 0)?) {
                v(ctx, k + 1, 0)?
            } else {
                v(ctx, k - 1, 0)? + 1
            };
            let mut x = x_pick;
            let mut y = x - k;
            ms.x = x;
            ms.y = y;
            while x < n && y < m && comp(a, aoff + x, b, boff + y)? {
                x += 1;
                y += 1;
            }
            let dist_new = dist2(x, y, u_max, v_max);
            if x <= n && y <= m && dist_new < dist {
                dist = dist_new;
                x_max = x;
                y_max = y;
            }
            setv(ctx, k, 0, x)?;
            if odd != 0 && k >= (delta - (d - 1)) && k <= (delta + (d - 1)) && x >= v(ctx, k, 1)?
            {
                ms.u = x;
                ms.v = y;
                return Ok((2 * d - 1, None));
            }
            k -= 2;
        }

        if 2 * d > ctx.dmax {
            ctx.dmaxhit = 1;
            ms.x = x_max;
            ms.y = y_max;
            ms.u = u_max;
            ms.v = v_max;
            let (extra, faux) = find_faux_snake(a, aoff, n, b, boff, m, ms, d - 1)?;
            let used = if faux.first().copied().unwrap_or(Op::Null) == Op::Null {
                None
            } else {
                Some(faux)
            };
            return Ok((2 * (d - 1) + 1 + extra, used));
        }

        let mut k = d;
        while k >= -d {
            let kr = (n - m) + k;
            let x_pick = if k == d || (k != -d && v(ctx, kr - 1, 1)? < v(ctx, kr + 1, 1)?) {
                v(ctx, kr - 1, 1)?
            } else {
                v(ctx, kr + 1, 1)? - 1
            };
            let mut x = x_pick;
            let mut y = x - kr;
            ms.u = x;
            ms.v = y;
            while x > 0 && y > 0 && comp(a, aoff + x - 1, b, boff + y - 1)? {
                x -= 1;
                y -= 1;
            }
            let dist_new = dist2(x_max, y_max, x, y);
            if x >= 0 && y >= 0 && dist_new < dist {
                dist = dist_new;
                u_max = x;
                v_max = y;
            }
            setv(ctx, kr, 1, x)?;
            if odd == 0 && kr >= -d && kr <= d && x <= v(ctx, kr, 0)? {
                ms.x = x;
                ms.y = y;
                return Ok((2 * d, None));
            }
            k -= 2;
        }
    }
    Err("Logic Error: failed finding middle snake, contact maintainer".into())
}

fn edit(ctx: &mut Ctx, op: Op, off: i32, len: i32) -> Result<(), String> {
    if len == 0 || ctx.ses.is_empty() {
        return Ok(());
    }
    if ctx.si > ctx.simax {
        return Err("Logic Error: exceed edit script length; contact maintainer.".into());
    }
    if ctx.ses[ctx.si as usize].op != op {
        if ctx.ses[ctx.si as usize].op != Op::Null {
            ctx.si += 1;
            if ctx.si > ctx.simax {
                return Err("Logic Error: exceed edit script length; contact maintainer.".into());
            }
        }
        let slot = &mut ctx.ses[ctx.si as usize];
        slot.op = op;
        slot.off = off;
        slot.len = len;
    } else {
        ctx.ses[ctx.si as usize].len += len;
    }
    Ok(())
}

fn edit_faux(ctx: &mut Ctx, faux: &[Op], mut aoff: i32, mut boff: i32) -> Result<(), String> {
    for &op in faux {
        let off = match op {
            Op::Match => {
                boff += 1;
                let off = aoff;
                aoff += 1;
                off
            }
            Op::Delete => {
                let off = aoff;
                aoff += 1;
                off
            }
            Op::Insert => {
                let off = boff;
                boff += 1;
                off
            }
            Op::Null => {
                return Err(
                    "Logic Error: unexpected faux snake instruction; contact maintainer".into(),
                );
            }
        };
        edit(ctx, op, off, 1)?;
    }
    Ok(())
}

fn ses(
    a: &[&str],
    mut aoff: i32,
    mut n: i32,
    b: &[&str],
    mut boff: i32,
    mut m: i32,
    ctx: &mut Ctx,
) -> Result<i32, String> {
    if n == 0 {
        edit(ctx, Op::Insert, boff, m)?;
        return Ok(m);
    }
    if m == 0 {
        edit(ctx, Op::Delete, aoff, n)?;
        return Ok(n);
    }
    let mut ms = Middle {
        x: 0,
        y: 0,
        u: 0,
        v: 0,
    };
    let (d, faux) = find_middle_snake(a, aoff, n, b, boff, m, ctx, &mut ms)?;
    if d == -1 {
        return Err("Logic error: failed trying to find middle snake, contact maintainer.".into());
    }
    if d != 1 {
        if ses(a, aoff, ms.x, b, boff, ms.y, ctx)? == -1 {
            return Err("Logic error: failed trying to run ses; contact maintainer.".into());
        }
        if let Some(faux) = faux {
            edit_faux(ctx, &faux, aoff + ms.x, boff + ms.y)?;
        } else {
            edit(ctx, Op::Match, aoff + ms.x, ms.u - ms.x)?;
        }
        aoff += ms.u;
        boff += ms.v;
        n -= ms.u;
        m -= ms.v;
        if ses(a, aoff, n, b, boff, m, ctx)? == -1 {
            return Err("Logic error: failed trying to run ses 2; contact maintainer.".into());
        }
    } else {
        let x = ms.x;
        let u = ms.u;
        if m > n {
            if x == u {
                edit(ctx, Op::Match, aoff, n)?;
                edit(ctx, Op::Insert, boff + (m - 1), 1)?;
            } else {
                edit(ctx, Op::Insert, boff, 1)?;
                edit(ctx, Op::Match, aoff, n)?;
            }
        } else if m < n {
            if x == u {
                edit(ctx, Op::Match, aoff, m)?;
                edit(ctx, Op::Delete, aoff + (n - 1), 1)?;
            } else {
                edit(ctx, Op::Delete, aoff, 1)?;
                edit(ctx, Op::Match, aoff + 1, m)?;
            }
        } else {
            return Err(format!(
                "Logic Error: special case d {d} n {n} m {m} aoff {aoff} boff {boff} u {}; contact maintainer\n",
                ms.u
            ));
        }
    }
    Ok(d)
}

#[cfg(feature = "python")]
mod py {
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::PyList;

    use crate::myers_diff;

    #[pyfunction]
    #[pyo3(name = "myers_diff")]
    fn myers_diff_py<'py>(
        py: Python<'py>,
        a: Vec<String>,
        b: Vec<String>,
        max_diffs: i32,
    ) -> PyResult<(Bound<'py, PyList>, Bound<'py, PyList>, Bound<'py, PyList>, i32)> {
        let a_refs: Vec<&str> = a.iter().map(String::as_str).collect();
        let b_refs: Vec<&str> = b.iter().map(String::as_str).collect();
        let (edits, diffs) =
            myers_diff(&a_refs, &b_refs, max_diffs).map_err(PyValueError::new_err)?;
        let kind = PyList::new(py, edits.iter().map(|item| item.kind))?;
        let len = PyList::new(py, edits.iter().map(|item| item.len))?;
        let off = PyList::new(py, edits.iter().map(|item| item.off))?;
        Ok((kind, len, off, diffs))
    }

    #[pymodule]
    #[pyo3(name = "myersmba")]
    fn myersmba_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(myers_diff_py, m)?)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::myers_diff;

    fn kinds(a: &[&str], b: &[&str], max_diffs: i32) -> (Vec<(i32, i32, i32)>, i32) {
        let (edits, diffs) = myers_diff(a, b, max_diffs).unwrap();
        (
            edits
                .into_iter()
                .map(|item| (item.kind, item.len, item.off))
                .collect(),
            diffs,
        )
    }

    #[test]
    fn letters_example() {
        let a = ["a", "b", "c", "d", "e", "f"];
        let b = ["b", "CC", "DD", "d", "f"];
        let (edits, diffs) = kinds(&a, &b, -1);
        assert_eq!(
            edits,
            vec![
                (3, 1, 0),
                (1, 1, 1),
                (3, 1, 2),
                (2, 2, 1),
                (1, 1, 3),
                (3, 1, 4),
                (1, 1, 5),
            ]
        );
        assert_eq!(diffs, 5);
    }

    #[test]
    fn reverse_and_middle_and_failover() {
        let letters: Vec<String> = (b'a'..=b'h').map(|c| (c as char).to_string()).collect();
        let rev: Vec<String> = letters.iter().rev().cloned().collect();
        let a: Vec<&str> = letters.iter().map(String::as_str).collect();
        let b: Vec<&str> = rev.iter().map(String::as_str).collect();
        let (edits, diffs) = kinds(&a, &b, -1);
        assert_eq!(edits, vec![(3, 7, 0), (1, 1, 7), (2, 7, 1)]);
        assert_eq!(diffs, 14);

        let (edits, diffs) = kinds(&["a", "b", "c", "d"], &["a", "X", "c", "d"], -1);
        assert_eq!(edits, vec![(1, 1, 0), (3, 1, 1), (2, 1, 1), (1, 2, 2)]);
        assert_eq!(diffs, 2);

        let left: Vec<String> = (b'a'..=b'j').map(|c| (c as char).to_string()).collect();
        let right: Vec<String> = (b'A'..=b'J').map(|c| (c as char).to_string()).collect();
        let a: Vec<&str> = left.iter().map(String::as_str).collect();
        let b: Vec<&str> = right.iter().map(String::as_str).collect();
        let (edits, diffs) = kinds(&a, &b, 2);
        assert_eq!(
            edits,
            vec![
                (3, 2, 0),
                (2, 1, 0),
                (3, 1, 2),
                (2, 1, 1),
                (3, 1, 3),
                (2, 1, 2),
                (3, 1, 4),
                (2, 1, 3),
                (3, 1, 5),
                (2, 1, 4),
                (3, 1, 6),
                (2, 1, 5),
                (3, 1, 7),
                (2, 1, 6),
                (3, 1, 8),
                (2, 1, 7),
                (3, 1, 9),
                (2, 2, 8),
            ]
        );
        assert_eq!(diffs, -20);
    }

    #[test]
    fn identical_and_empty() {
        let (edits, diffs) = kinds(&["a", "b"], &["a", "b"], -1);
        assert_eq!(edits, vec![(1, 2, 0)]);
        assert_eq!(diffs, 0);
        let (edits, diffs) = kinds(&[], &[], -1);
        assert!(edits.is_empty());
        assert_eq!(diffs, 0);
        let (edits, diffs) = kinds(&[], &["a"], -1);
        assert_eq!(edits, vec![(2, 1, 0)]);
        assert_eq!(diffs, 1);
    }
}
