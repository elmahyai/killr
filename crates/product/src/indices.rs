//! Index rules from matrixStats `src/validateIndices.c`.
//!
//! `idxs` is 1-based. `None` in the Python wrapper is [`Idxs::All`].
//! Positive indexes that fall past the vector become missing. Zeros are
//! dropped. Negative indexes exclude those positions. Logical indexes are
//! recycled, and a logical value past the end becomes a missing index.

/// R's `NA_integer_`.
pub const NA_INTEGER: i64 = i32::MIN as i64;

/// How `idxs` was supplied. Logical codes are `1` true, `0` false, and `-1` missing.
#[derive(Debug, Clone, Copy)]
pub enum Idxs<'a> {
    All,
    Integer(&'a [i64]),
    Real(&'a [f64]),
    Logical(&'a [i8]),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct IndexError {
    pub message: &'static str,
}

impl IndexError {
    const MIXED: Self = Self {
        message: "only 0's may be mixed with negative subscripts",
    };
    const OUT_OF_BOUNDS: Self = Self {
        message: "subscript out of bounds",
    };
    const LOGICAL_LONG: Self = Self {
        message: "logical subscript too long",
    };
}

impl std::fmt::Display for IndexError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.message)
    }
}

impl std::error::Error for IndexError {}

/// Resolved positions. `None` is a missing index and yields a missing value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Selection {
    All,
    Pick(Vec<Option<usize>>),
}

pub(crate) fn resolve(idxs: Idxs<'_>, n: usize, allow_oob: bool) -> Result<Selection, IndexError> {
    match idxs {
        Idxs::All => Ok(Selection::All),
        Idxs::Integer(values) => resolve_integer(values, n, allow_oob),
        Idxs::Real(values) => resolve_real(values, n, allow_oob),
        Idxs::Logical(values) => resolve_logical(values, n, allow_oob),
    }
}

fn resolve_integer(idxs: &[i64], n: usize, allow_oob: bool) -> Result<Selection, IndexError> {
    let max_idx = n as i64;
    let mut state = 0i8;
    for &idx in idxs {
        if idx == NA_INTEGER || idx > 0 {
            if state < 0 {
                return Err(IndexError::MIXED);
            }
            if idx != NA_INTEGER && idx > max_idx && !allow_oob {
                return Err(IndexError::OUT_OF_BOUNDS);
            }
            state = 1;
        } else if idx < 0 {
            if state > 0 {
                return Err(IndexError::MIXED);
            }
            state = -1;
        }
    }
    if state < 0 {
        return Ok(exclude(
            n,
            idxs.iter().filter_map(|&idx| {
                let mag = idx.checked_neg()?;
                if mag > 0 && mag <= max_idx {
                    Some(mag as usize)
                } else {
                    None
                }
            }),
        ));
    }
    let mut picked = Vec::new();
    for &idx in idxs {
        if idx == 0 {
            continue;
        }
        picked.push(positive_integer(idx, max_idx));
    }
    Ok(Selection::Pick(picked))
}

fn positive_integer(idx: i64, max_idx: i64) -> Option<usize> {
    if idx == NA_INTEGER || idx > max_idx {
        return None;
    }
    let zero_based = idx - 1;
    if zero_based < 0 {
        Some(0)
    } else {
        Some(zero_based as usize)
    }
}

fn resolve_real(idxs: &[f64], n: usize, allow_oob: bool) -> Result<Selection, IndexError> {
    let max_idx = n as i64;
    let max_as_float = max_idx as f64;
    let mut state = 0i8;
    for &idx in idxs {
        if idx > 0.0 || idx.is_nan() || idx.is_infinite() {
            if state < 0 {
                return Err(IndexError::MIXED);
            }
            // Infinity is a missing index. It does not take the out-of-bounds error.
            if !idx.is_nan() && !idx.is_infinite() && idx > max_as_float && !allow_oob {
                return Err(IndexError::OUT_OF_BOUNDS);
            }
            state = 1;
        } else if idx < 0.0 {
            if state > 0 {
                return Err(IndexError::MIXED);
            }
            state = -1;
        }
    }
    if state < 0 {
        return Ok(exclude(
            n,
            idxs.iter().filter_map(|&idx| {
                if !(idx < 0.0) || idx.is_infinite() {
                    return None;
                }
                let mag = -idx;
                if mag > max_as_float {
                    return None;
                }
                let truncated = mag as i64;
                if truncated > 0 && truncated <= max_idx {
                    Some(truncated as usize)
                } else {
                    None
                }
            }),
        ));
    }
    let mut picked = Vec::new();
    for &idx in idxs {
        if idx == 0.0 {
            continue;
        }
        picked.push(positive_real(idx, max_as_float));
    }
    Ok(Selection::Pick(picked))
}

fn positive_real(idx: f64, max_as_float: f64) -> Option<usize> {
    if idx.is_nan() || idx.is_infinite() || idx > max_as_float {
        return None;
    }
    // `R_xlen_t` truncates toward zero after subtracting one. Values in (0, 1)
    // therefore select the first element.
    let zero_based = (idx - 1.0) as i64;
    if zero_based < 0 {
        Some(0)
    } else {
        Some(zero_based as usize)
    }
}

fn exclude(n: usize, drop_ones_based: impl Iterator<Item = usize>) -> Selection {
    if n == 0 {
        return Selection::Pick(Vec::new());
    }
    let mut dropped = vec![false; n];
    let mut kept = n;
    for pos in drop_ones_based {
        if (1..=n).contains(&pos) && !dropped[pos - 1] {
            dropped[pos - 1] = true;
            kept -= 1;
        }
    }
    if kept == 0 {
        return Selection::Pick(Vec::new());
    }
    let mut picked = Vec::with_capacity(kept);
    for (i, is_dropped) in dropped.iter().enumerate() {
        if !is_dropped {
            picked.push(Some(i));
        }
    }
    Selection::Pick(picked)
}

fn resolve_logical(idxs: &[i8], n: usize, allow_oob: bool) -> Result<Selection, IndexError> {
    let nidxs = idxs.len();
    if nidxs == 0 {
        return Ok(Selection::Pick(Vec::new()));
    }
    if nidxs > n {
        if !allow_oob {
            return Err(IndexError::LOGICAL_LONG);
        }
        let mut picked = Vec::new();
        for (ii, &value) in idxs.iter().take(n).enumerate() {
            if value != 0 {
                picked.push(if value < 0 { None } else { Some(ii) });
            }
        }
        let extra = idxs.iter().skip(n).filter(|&&value| value != 0).count();
        picked.extend(std::iter::repeat(None).take(extra));
        return Ok(Selection::Pick(picked));
    }

    let last_part = n % nidxs;
    let mut count1 = 0usize;
    let mut na_count = 0usize;
    for &value in idxs.iter().take(last_part) {
        if value != 0 {
            if value < 0 {
                na_count += 1;
            }
            count1 += 1;
        }
    }
    let mut count2 = 0usize;
    for &value in idxs.iter().skip(last_part) {
        if value != 0 {
            if value < 0 {
                na_count += 1;
            }
            count2 += 1;
        }
    }
    let count = count1 + count2;
    if na_count == 0 && count == nidxs {
        return Ok(Selection::All);
    }

    let mut picked = Vec::with_capacity(n / nidxs * count + count1);
    for (ii, &value) in idxs.iter().enumerate() {
        if value != 0 {
            picked.push(if value < 0 { None } else { Some(ii) });
        }
    }
    let mut offset = nidxs;
    while offset + nidxs <= n {
        for slot in 0..count {
            picked.push(shift(picked[slot], offset));
        }
        offset += nidxs;
    }
    for slot in 0..count1 {
        picked.push(shift(picked[slot], offset));
    }
    Ok(Selection::Pick(picked))
}

fn shift(index: Option<usize>, offset: usize) -> Option<usize> {
    index.map(|pos| pos + offset)
}
