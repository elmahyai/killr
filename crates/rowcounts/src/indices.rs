//! Index rules from matrixStats `src/validateIndices.c`.
//!
//! Indices are 1-based. `None` selects every position. Zero is dropped.
//! Negatives exclude those positions. An integer NA, a non-finite real, or a
//! logical NA is a missing index and reads as a missing value.
//!
//! Row and column margins pass `allow_out_of_bounds = false` and a positive
//! index past the end is `"subscript out of bounds"`. `count` passes `true`:
//! a positive index past the end, and a logical `TRUE` past the end, is a
//! missing element.

/// R's message for a mix of positive and negative subscripts.
const MIXED_SIGN: &str = "only 0's may be mixed with negative subscripts";

/// Which positions to read. `None` inside [`Subset::At`] is a missing index.
#[derive(Clone, Debug, PartialEq)]
pub enum Subset {
    /// Every position, in order. This is R's `NULL`.
    All,
    /// Resolved 0-based positions. `None` is a missing subscript.
    At(Vec<Option<usize>>),
}

/// 1-based integer indices. `i32::MIN` is R's integer NA.
pub fn validate_int(
    idxs: &[i64],
    max_idx: usize,
    allow_out_of_bounds: bool,
) -> Result<Subset, String> {
    if idxs.is_empty() {
        return Ok(Subset::At(Vec::new()));
    }

    let mut state = 0_i8;
    let mut count = 0_usize;
    let mut need_realloc = false;

    for &idx in idxs {
        if idx > 0 || is_int_na(idx) {
            if state < 0 {
                return Err(MIXED_SIGN.to_string());
            }
            if !is_int_na(idx) && exceeds_i64(idx, max_idx) {
                if !allow_out_of_bounds {
                    return Err("subscript out of bounds".to_string());
                }
                need_realloc = true;
            }
            state = 1;
            count += 1;
        } else if idx < 0 {
            if state > 0 {
                return Err(MIXED_SIGN.to_string());
            }
            state = -1;
            need_realloc = true;
        } else {
            need_realloc = true;
        }
    }

    if state >= 0 && !need_realloc {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            ans.push(int_to_zero_based(idx, max_idx));
        }
        return Ok(Subset::At(ans));
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            if idx != 0 {
                ans.push(int_to_zero_based(idx, max_idx));
            }
        }
        return Ok(Subset::At(ans));
    }

    exclude_negatives(idxs.iter().copied(), max_idx)
}

/// 1-based real indices. NaN and both infinities are NA indices.
pub fn validate_real(
    idxs: &[f64],
    max_idx: usize,
    allow_out_of_bounds: bool,
) -> Result<Subset, String> {
    if idxs.is_empty() {
        return Ok(Subset::At(Vec::new()));
    }

    let mut state = 0_i8;
    let mut count = 0_usize;
    let mut need_realloc = false;

    for &idx in idxs {
        if idx > 0.0 || !idx.is_finite() {
            if state < 0 {
                return Err(MIXED_SIGN.to_string());
            }
            if idx.is_finite() && idx > max_idx as f64 {
                if !allow_out_of_bounds {
                    return Err("subscript out of bounds".to_string());
                }
                need_realloc = true;
            }
            if !idx.is_finite() {
                need_realloc = true;
            }
            state = 1;
            count += 1;
        } else if idx < 0.0 {
            if state > 0 {
                return Err(MIXED_SIGN.to_string());
            }
            state = -1;
            need_realloc = true;
        } else {
            need_realloc = true;
        }
    }

    if state >= 0 && !need_realloc {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            ans.push(real_to_zero_based(idx, max_idx));
        }
        return Ok(Subset::At(ans));
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            if idx != 0.0 {
                ans.push(real_to_zero_based(idx, max_idx));
            }
        }
        return Ok(Subset::At(ans));
    }

    let mut drop = vec![false; max_idx];
    let mut kept = max_idx;
    for &idx in idxs {
        let excl = (-idx).trunc();
        if excl > 0.0 && excl <= max_idx as f64 {
            let pos = (excl as usize) - 1;
            if !drop[pos] {
                drop[pos] = true;
                kept -= 1;
            }
        }
    }
    if kept == 0 {
        return Ok(Subset::At(Vec::new()));
    }
    let mut ans = Vec::with_capacity(kept);
    for (pos, dropped) in drop.into_iter().enumerate() {
        if !dropped {
            ans.push(Some(pos));
        }
    }
    Ok(Subset::At(ans))
}

/// Logical indices. `1` is TRUE, `0` is FALSE, and any negative value is NA.
/// A pattern shorter than the margin is recycled, matching R.
pub fn validate_logical(
    idxs: &[i8],
    max_idx: usize,
    allow_out_of_bounds: bool,
) -> Result<Subset, String> {
    let nidxs = idxs.len();
    if nidxs == 0 {
        return Ok(Subset::At(Vec::new()));
    }
    if nidxs > max_idx {
        if !allow_out_of_bounds {
            return Err("logical subscript too long".to_string());
        }
        let mut ans = Vec::new();
        for (ii, &flag) in idxs.iter().enumerate() {
            if flag == 0 {
                continue;
            }
            if ii < max_idx && flag > 0 {
                ans.push(Some(ii));
            } else {
                ans.push(None);
            }
        }
        return Ok(Subset::At(ans));
    }

    let last_part = max_idx % nidxs;
    let mut count1 = 0_usize;
    let mut count2 = 0_usize;
    let mut na_count = 0_usize;
    for (ii, &flag) in idxs.iter().enumerate() {
        if flag != 0 {
            if flag < 0 {
                na_count += 1;
            }
            if ii < last_part {
                count1 += 1;
            } else {
                count2 += 1;
            }
        }
    }
    let count = count1 + count2;
    if na_count == 0 && count == nidxs {
        return Ok(Subset::All);
    }

    let ans_n = (max_idx / nidxs) * count + count1;
    let mut first = Vec::with_capacity(count);
    for (ii, &flag) in idxs.iter().enumerate() {
        if flag != 0 {
            if flag < 0 {
                first.push(None);
            } else {
                first.push(Some(ii));
            }
        }
    }

    let mut ans = Vec::with_capacity(ans_n);
    ans.extend_from_slice(&first);
    let mut kk = nidxs;
    while kk + nidxs <= max_idx {
        for item in &first {
            ans.push(item.map(|pos| pos + kk));
        }
        kk += nidxs;
    }
    for item in first.iter().take(count1) {
        ans.push(item.map(|pos| pos + kk));
    }
    Ok(Subset::At(ans))
}

pub fn margin_len(subset: &Subset, n: usize) -> usize {
    match subset {
        Subset::All => n,
        Subset::At(idx) => idx.len(),
    }
}

pub fn margin_at(subset: &Subset, i: usize) -> Option<usize> {
    match subset {
        Subset::All => Some(i),
        Subset::At(idx) => idx[i],
    }
}

fn exceeds_i64(idx: i64, max_idx: usize) -> bool {
    if max_idx > i64::MAX as usize {
        false
    } else {
        idx > max_idx as i64
    }
}

fn is_int_na(idx: i64) -> bool {
    idx == i32::MIN as i64
}

fn int_to_zero_based(idx: i64, max_idx: usize) -> Option<usize> {
    if is_int_na(idx) || idx < 1 || exceeds_i64(idx, max_idx) {
        None
    } else {
        Some((idx as usize) - 1)
    }
}

fn real_to_zero_based(idx: f64, max_idx: usize) -> Option<usize> {
    if !idx.is_finite() || idx > max_idx as f64 {
        return None;
    }
    // C converts `idx - 1` to an integer by truncating toward zero.
    let zero_based = (idx - 1.0).trunc();
    if zero_based <= 0.0 {
        Some(0)
    } else {
        Some(zero_based as usize)
    }
}

fn exclude_negatives(idxs: impl Iterator<Item = i64>, max_idx: usize) -> Result<Subset, String> {
    let mut drop = vec![false; max_idx];
    let mut kept = max_idx;
    for idx in idxs {
        let Some(excl) = idx.checked_neg() else {
            continue;
        };
        if excl > 0 && (excl as usize) <= max_idx {
            let pos = (excl as usize) - 1;
            if !drop[pos] {
                drop[pos] = true;
                kept -= 1;
            }
        }
    }
    if kept == 0 {
        return Ok(Subset::At(Vec::new()));
    }
    let mut ans = Vec::with_capacity(kept);
    for (pos, dropped) in drop.into_iter().enumerate() {
        if !dropped {
            ans.push(Some(pos));
        }
    }
    Ok(Subset::At(ans))
}
