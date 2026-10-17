//! Index rules from matrixStats `src/validateIndices.c`.
//!
//! Positions are 0-based. [`NA_POSITION`] is an NA index: out of bounds when
//! out-of-bounds indexes are allowed, an NA subscript, or a non-finite real
//! subscript. `signTabulate` reads an NA index as a missing value.
//!
//! `None` from the logical validator means every element, which is what an
//! all-TRUE subscript selects. Integer and real subscripts never use that
//! shortcut. `signTabulate` calls validation with out-of-bounds indexes allowed.

/// 0-based stand-in for R's `NA_R_XLEN_T`.
pub const NA_POSITION: i64 = i64::MIN;

/// R's integer NA, `NA_INTEGER`.
pub const NA_INTEGER: i64 = i32::MIN as i64;

/// `None` selects every element. `Some` is the 0-based positions to visit.
pub type Positions = Option<Vec<i64>>;

fn int_is_na(idx: i64) -> bool {
    idx == NA_INTEGER
}

fn real_is_na(idx: f64) -> bool {
    idx.is_nan() || idx.is_infinite()
}

fn collect_excluded(max_idx: i64, magnitudes: impl Iterator<Item = i64>) -> Vec<i64> {
    if max_idx <= 0 {
        return Vec::new();
    }
    let n = max_idx as usize;
    let mut excluded = vec![false; n];
    let mut kept = max_idx;
    for mag in magnitudes {
        if mag > 0 && mag <= max_idx {
            let pos = (mag as usize) - 1;
            if !excluded[pos] {
                excluded[pos] = true;
                kept -= 1;
            }
        }
    }
    if kept == 0 {
        return Vec::new();
    }
    let mut upper = n;
    while upper > 0 && excluded[upper - 1] {
        upper -= 1;
    }
    let mut ans = Vec::with_capacity(kept as usize);
    for (i, dropped) in excluded.iter().enumerate().take(upper) {
        if !dropped {
            ans.push(i as i64);
        }
    }
    ans
}

fn real_magnitude(idx: f64) -> i64 {
    let mag = -idx;
    if !mag.is_finite() || mag >= i64::MAX as f64 {
        return i64::MAX;
    }
    mag as i64
}

fn real_position(idx: f64, max_idx: i64) -> i64 {
    if real_is_na(idx) || idx > max_idx as f64 {
        NA_POSITION
    } else {
        (idx - 1.0) as i64
    }
}

fn int_position(idx: i64, max_idx: i64) -> i64 {
    if int_is_na(idx) || idx > max_idx {
        NA_POSITION
    } else {
        idx - 1
    }
}

/// Validate 1-based integer subscripts. `NA_INTEGER` is an NA subscript.
pub fn positions_from_integer(
    idxs: &[i64],
    max_idx: i64,
    allow_out_of_bounds: bool,
) -> Result<Vec<i64>, String> {
    if idxs.is_empty() {
        return Ok(Vec::new());
    }

    let mut state: i8 = 0;
    for &idx in idxs {
        if int_is_na(idx) || idx > 0 {
            if state < 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            if !int_is_na(idx) && idx > max_idx && !allow_out_of_bounds {
                return Err("subscript out of bounds".to_string());
            }
            state = 1;
        } else if idx < 0 {
            if state > 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            state = -1;
        }
    }

    if state >= 0 {
        let mut ans = Vec::new();
        for &idx in idxs {
            if idx != 0 {
                ans.push(int_position(idx, max_idx));
            }
        }
        return Ok(ans);
    }

    Ok(collect_excluded(
        max_idx,
        idxs.iter().filter_map(|&idx| {
            if idx >= 0 {
                return None;
            }
            if idx == i64::MIN {
                return Some(i64::MAX);
            }
            Some(-idx)
        }),
    ))
}

/// Validate 1-based real subscripts. Non-finite values are NA subscripts.
///
/// The bounds check uses the real value before truncation, matching
/// `R_xlen_t_from_idx`. `3.2` on a length-3 vector is out of bounds, while
/// `2.9` truncates to element 2.
pub fn positions_from_real(
    idxs: &[f64],
    max_idx: i64,
    allow_out_of_bounds: bool,
) -> Result<Vec<i64>, String> {
    if idxs.is_empty() {
        return Ok(Vec::new());
    }

    let mut state: i8 = 0;
    for &idx in idxs {
        if real_is_na(idx) || idx > 0.0 {
            if state < 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            if !real_is_na(idx) && idx > max_idx as f64 && !allow_out_of_bounds {
                return Err("subscript out of bounds".to_string());
            }
            state = 1;
        } else if idx < 0.0 {
            if state > 0 {
                return Err("only 0's may be mixed with negative subscripts".to_string());
            }
            state = -1;
        }
    }

    if state >= 0 {
        let mut ans = Vec::new();
        for &idx in idxs {
            if idx != 0.0 {
                ans.push(real_position(idx, max_idx));
            }
        }
        return Ok(ans);
    }

    Ok(collect_excluded(
        max_idx,
        idxs.iter().filter_map(|&idx| {
            if idx < 0.0 && idx.is_finite() {
                Some(real_magnitude(idx))
            } else {
                None
            }
        }),
    ))
}

/// Validate a logical subscript.
///
/// `1` is TRUE, `0` is FALSE, and any other value is NA. `Ok(None)` means
/// every element. A logical subscript longer than `max_idx` is an error when
/// out-of-bounds indexes are refused; otherwise each extra TRUE or NA becomes
/// an NA index.
pub fn positions_from_logical(
    flags: &[i8],
    max_idx: i64,
    allow_out_of_bounds: bool,
) -> Result<Positions, String> {
    let nidxs = flags.len() as i64;
    if nidxs == 0 {
        return Ok(Some(Vec::new()));
    }
    if max_idx < 0 {
        return Err("subscript out of bounds".to_string());
    }

    if nidxs > max_idx {
        if !allow_out_of_bounds {
            return Err("logical subscript too long".to_string());
        }
        let mut ans = Vec::new();
        for (ii, &flag) in flags.iter().enumerate() {
            if flag == 0 {
                continue;
            }
            if (ii as i64) < max_idx && flag == 1 {
                ans.push(ii as i64);
            } else {
                ans.push(NA_POSITION);
            }
        }
        return Ok(Some(ans));
    }

    let last_part = (max_idx % nidxs) as usize;
    let mut count1 = 0usize;
    let mut count2 = 0usize;
    let mut na_count = 0usize;
    for (ii, &flag) in flags.iter().enumerate() {
        if flag == 0 {
            continue;
        }
        if flag != 1 {
            na_count += 1;
        }
        if ii < last_part {
            count1 += 1;
        } else {
            count2 += 1;
        }
    }
    let count = count1 + count2;
    if na_count == 0 && count == flags.len() {
        return Ok(None);
    }

    let n_full = (max_idx / nidxs) as usize;
    let ans_len = n_full * count + count1;
    let mut ans = vec![0; ans_len];
    let mut cursor = 0usize;
    for (ii, &flag) in flags.iter().enumerate() {
        if flag == 0 {
            continue;
        }
        ans[cursor] = if flag == 1 { ii as i64 } else { NA_POSITION };
        cursor += 1;
    }

    let mut ii = count;
    let mut kk = nidxs;
    while kk + nidxs <= max_idx {
        for slot in 0..count {
            ans[ii + slot] = if ans[slot] == NA_POSITION {
                NA_POSITION
            } else {
                ans[slot] + kk
            };
        }
        ii += count;
        kk += nidxs;
    }
    for slot in 0..count1 {
        ans[ii + slot] = if ans[slot] == NA_POSITION {
            NA_POSITION
        } else {
            ans[slot] + kk
        };
    }
    Ok(Some(ans))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn positive_integer_positions_are_zero_based() {
        let pos = positions_from_integer(&[2, 2, 1], 4, true).unwrap();
        assert_eq!(pos, vec![1, 1, 0]);
    }

    #[test]
    fn zeros_are_dropped_and_out_of_bounds_is_na() {
        let pos = positions_from_integer(&[0, 2, 0, 9], 3, true).unwrap();
        assert_eq!(pos, vec![1, NA_POSITION]);
    }

    #[test]
    fn integer_na_is_an_na_index() {
        let pos = positions_from_integer(&[NA_INTEGER], 3, true).unwrap();
        assert_eq!(pos, vec![NA_POSITION]);
    }

    #[test]
    fn negative_subscripts_exclude_positions() {
        let pos = positions_from_integer(&[-1, -1, 0], 4, true).unwrap();
        assert_eq!(pos, vec![1, 2, 3]);
    }

    #[test]
    fn mixed_signs_are_rejected() {
        let err = positions_from_integer(&[1, -1], 3, true).unwrap_err();
        assert_eq!(err, "only 0's may be mixed with negative subscripts");
    }

    #[test]
    fn out_of_bounds_can_be_refused() {
        let err = positions_from_integer(&[4], 3, false).unwrap_err();
        assert_eq!(err, "subscript out of bounds");
    }

    #[test]
    fn real_fractional_indexes_truncate_after_the_bounds_check() {
        assert_eq!(positions_from_real(&[2.9], 3, true).unwrap(), vec![1]);
        assert_eq!(
            positions_from_real(&[3.2], 3, true).unwrap(),
            vec![NA_POSITION]
        );
        assert_eq!(positions_from_real(&[0.5], 3, true).unwrap(), vec![0]);
    }

    #[test]
    fn negative_real_fraction_excludes_the_truncated_position() {
        let pos = positions_from_real(&[-1.9], 3, true).unwrap();
        assert_eq!(pos, vec![1, 2]);
    }

    #[test]
    fn non_finite_real_subscripts_are_na_indexes() {
        assert_eq!(
            positions_from_real(&[f64::NAN], 3, true).unwrap(),
            vec![NA_POSITION]
        );
        assert_eq!(
            positions_from_real(&[f64::INFINITY], 3, true).unwrap(),
            vec![NA_POSITION]
        );
        assert_eq!(
            positions_from_real(&[f64::NEG_INFINITY], 3, true).unwrap(),
            vec![NA_POSITION]
        );
    }

    #[test]
    fn logical_recycling_and_all_true() {
        assert!(positions_from_logical(&[1], 4, true).unwrap().is_none());
        assert_eq!(
            positions_from_logical(&[1, 0], 4, true).unwrap().unwrap(),
            vec![0, 2]
        );
        assert_eq!(
            positions_from_logical(&[1, 0, -1], 5, true)
                .unwrap()
                .unwrap(),
            vec![0, NA_POSITION, 3]
        );
        assert!(positions_from_logical(&[0], 4, true)
            .unwrap()
            .unwrap()
            .is_empty());
    }

    #[test]
    fn logical_longer_than_the_vector_adds_na_indexes() {
        assert_eq!(
            positions_from_logical(&[0, 0, 1], 2, true).unwrap().unwrap(),
            vec![NA_POSITION]
        );
        assert!(positions_from_logical(&[0, 0, 0], 2, true)
            .unwrap()
            .unwrap()
            .is_empty());
        let err = positions_from_logical(&[0, 0, 1], 2, false).unwrap_err();
        assert_eq!(err, "logical subscript too long");
    }
}
