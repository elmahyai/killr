//! Subset rules from matrixStats `src/validateIndices.c`.
//!
//! `logSumExp` calls `validateIndicesCheckNA` with out-of-bounds allowed.
//! Indices are 1-based. Zero is dropped. A positive index past the vector,
//! `NaN`, or infinity becomes a missing element. Negative indices drop
//! those positions. A logical vector is recycled, and logical values past
//! the vector become missing when they are true.

/// R's message for a mix of positive and negative subscripts.
pub const MIXED_SIGN: &str = "only 0's may be mixed with negative subscripts";

/// Which elements to read. `None` inside [`IndexSpec::At`] is a missing index.
#[derive(Clone, Debug, PartialEq)]
pub enum IndexSpec {
    /// Every element, in order. This is R's `idxs = NULL`.
    All,
    /// Resolved 0-based positions. `None` is a missing subscript.
    At(Vec<Option<usize>>),
}

/// One integer subscript. `Missing` is R's `NA_integer_`.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum IntItem {
    Value(i64),
    Missing,
}

/// One logical subscript.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Logical {
    False,
    True,
    Na,
}

/// Resolve 1-based integer subscripts against a vector of length `n`.
pub fn resolve_i64(idxs: &[IntItem], n: usize) -> Result<IndexSpec, &'static str> {
    if idxs.is_empty() {
        return Ok(IndexSpec::At(Vec::new()));
    }
    let max_idx = n as i64;
    let mut state = 0_i8;
    let mut count = 0_usize;

    for item in idxs {
        if positive_int(item) {
            if state < 0 {
                return Err(MIXED_SIGN);
            }
            state = 1;
            count += 1;
        } else if negative_int(item) {
            if state > 0 {
                return Err(MIXED_SIGN);
            }
            state = -1;
        }
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for item in idxs {
            match item {
                IntItem::Missing => ans.push(None),
                IntItem::Value(0) => {}
                IntItem::Value(value) => ans.push(from_idx_int(*value, max_idx)),
            }
        }
        return Ok(IndexSpec::At(ans));
    }

    Ok(IndexSpec::At(positions_after_exclusion(
        n,
        idxs.iter().filter_map(|item| match item {
            IntItem::Value(value) if *value < 0 => Some(exclude_from_negative_int(*value)),
            _ => None,
        }),
    )))
}

/// Resolve 1-based numeric subscripts. Non-finite values are missing indices.
pub fn resolve_f64(idxs: &[f64], n: usize) -> Result<IndexSpec, &'static str> {
    if idxs.is_empty() {
        return Ok(IndexSpec::At(Vec::new()));
    }
    let max_idx = n as i64;
    let mut state = 0_i8;
    let mut count = 0_usize;

    for &idx in idxs {
        if positive_real(idx) {
            if state < 0 {
                return Err(MIXED_SIGN);
            }
            state = 1;
            count += 1;
        } else if idx < 0.0 {
            if state > 0 {
                return Err(MIXED_SIGN);
            }
            state = -1;
        }
    }

    if state >= 0 {
        let mut ans = Vec::with_capacity(count);
        for &idx in idxs {
            // C treats the subscript as true when it is not zero, including NaN.
            if idx != 0.0 {
                ans.push(from_idx_real(idx, max_idx));
            }
        }
        return Ok(IndexSpec::At(ans));
    }

    Ok(IndexSpec::At(positions_after_exclusion(
        n,
        idxs.iter()
            .copied()
            .filter(|idx| *idx < 0.0)
            .map(exclude_from_negative_real),
    )))
}

/// Resolve a logical subscript, recycling it to length `n`.
pub fn resolve_logical(idxs: &[Logical], n: usize) -> IndexSpec {
    let nidxs = idxs.len();
    if nidxs == 0 {
        return IndexSpec::At(Vec::new());
    }
    if nidxs > n {
        let mut ans = Vec::new();
        for (ii, item) in idxs.iter().enumerate() {
            if ii < n {
                match item {
                    Logical::True => ans.push(Some(ii)),
                    Logical::Na => ans.push(None),
                    Logical::False => {}
                }
            } else if !matches!(item, Logical::False) {
                ans.push(None);
            }
        }
        return IndexSpec::At(ans);
    }

    let last_part = n % nidxs;
    let mut na_count = 0_usize;
    let mut count1 = 0_usize;
    let mut count2 = 0_usize;
    for (ii, item) in idxs.iter().enumerate() {
        if matches!(item, Logical::False) {
            continue;
        }
        if matches!(item, Logical::Na) {
            na_count += 1;
        }
        if ii < last_part {
            count1 += 1;
        } else {
            count2 += 1;
        }
    }
    let count = count1 + count2;
    if na_count == 0 && count == nidxs {
        return IndexSpec::All;
    }

    let mut first = Vec::with_capacity(count);
    for (ii, item) in idxs.iter().enumerate() {
        match item {
            Logical::True => first.push(Some(ii)),
            Logical::Na => first.push(None),
            Logical::False => {}
        }
    }

    let periods = n / nidxs;
    let mut ans = Vec::with_capacity(periods * count + count1);
    for period in 0..periods {
        let offset = period * nidxs;
        for item in &first {
            ans.push(item.map(|index| index + offset));
        }
    }
    let offset = periods * nidxs;
    for item in first.iter().take(count1) {
        ans.push(item.map(|index| index + offset));
    }
    IndexSpec::At(ans)
}

fn positive_int(item: &IntItem) -> bool {
    match item {
        IntItem::Missing => true,
        IntItem::Value(value) => *value > 0,
    }
}

fn negative_int(item: &IntItem) -> bool {
    matches!(item, IntItem::Value(value) if *value < 0)
}

fn positive_real(idx: f64) -> bool {
    idx > 0.0 || idx.is_nan() || idx.is_infinite()
}

fn from_idx_int(value: i64, max_idx: i64) -> Option<usize> {
    if value > max_idx || value < 1 {
        None
    } else {
        Some((value - 1) as usize)
    }
}

fn from_idx_real(value: f64, max_idx: i64) -> Option<usize> {
    if !value.is_finite() || value > max_idx as f64 {
        return None;
    }
    // C converts `value - 1` to an integer by truncating toward zero.
    let zero_based = (value - 1.0).trunc();
    if zero_based < 0.0 || zero_based > max_idx as f64 {
        None
    } else {
        Some(zero_based as usize)
    }
}

fn exclude_from_negative_int(value: i64) -> i64 {
    value.checked_neg().unwrap_or(i64::MAX)
}

fn exclude_from_negative_real(idx: f64) -> i64 {
    let negated = -idx;
    if !negated.is_finite() || negated >= i64::MAX as f64 {
        i64::MAX
    } else {
        negated.trunc() as i64
    }
}

/// `exclude_1based` lists positions to drop. Values outside `1..=n` are ignored.
fn positions_after_exclusion(
    n: usize,
    exclude_1based: impl Iterator<Item = i64>,
) -> Vec<Option<usize>> {
    if n == 0 {
        return Vec::new();
    }
    let mut drop = vec![false; n];
    let mut kept = n;
    for idx in exclude_1based {
        if idx >= 1 && (idx as u64) <= (n as u64) {
            let slot = (idx as usize) - 1;
            if !drop[slot] {
                drop[slot] = true;
                kept -= 1;
            }
        }
    }
    let mut ans = Vec::with_capacity(kept);
    for (index, dropped) in drop.iter().enumerate() {
        if !dropped {
            ans.push(Some(index));
        }
    }
    ans
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn positive_indices_drop_zeros_and_keep_duplicates() {
        let spec = resolve_i64(
            &[
                IntItem::Value(3),
                IntItem::Value(0),
                IntItem::Value(0),
                IntItem::Value(5),
                IntItem::Value(1),
                IntItem::Value(5),
                IntItem::Value(5),
            ],
            6,
        )
        .unwrap();
        assert_eq!(
            spec,
            IndexSpec::At(vec![Some(2), Some(4), Some(0), Some(4), Some(4)])
        );
    }

    #[test]
    fn negative_indices_drop_those_positions_once() {
        let spec = resolve_i64(
            &[
                IntItem::Value(-4),
                IntItem::Value(0),
                IntItem::Value(0),
                IntItem::Value(-3),
                IntItem::Value(-1),
                IntItem::Value(-3),
                IntItem::Value(-1),
            ],
            6,
        )
        .unwrap();
        assert_eq!(spec, IndexSpec::At(vec![Some(1), Some(4), Some(5)]));
    }

    #[test]
    fn out_of_range_positive_is_missing_and_negative_is_ignored() {
        let high = resolve_i64(
            &[
                IntItem::Value(4),
                IntItem::Value(5),
                IntItem::Value(6),
                IntItem::Value(7),
                IntItem::Value(8),
                IntItem::Value(9),
            ],
            6,
        )
        .unwrap();
        assert_eq!(
            high,
            IndexSpec::At(vec![Some(3), Some(4), Some(5), None, None, None])
        );

        let low = resolve_i64(
            &[
                IntItem::Value(-5),
                IntItem::Value(0),
                IntItem::Value(-3),
                IntItem::Value(-1),
                IntItem::Value(-9),
            ],
            6,
        )
        .unwrap();
        assert_eq!(low, IndexSpec::At(vec![Some(1), Some(3), Some(5)]));
    }

    #[test]
    fn mixed_signs_are_rejected() {
        let err = resolve_i64(&[IntItem::Value(1), IntItem::Value(-1)], 4).unwrap_err();
        assert_eq!(err, MIXED_SIGN);
        let err = resolve_f64(&[f64::NAN, -2.0], 4).unwrap_err();
        assert_eq!(err, MIXED_SIGN);
    }

    #[test]
    fn fractional_positive_truncates_toward_zero() {
        let spec = resolve_f64(&[1.9, 2.1], 6).unwrap();
        assert_eq!(spec, IndexSpec::At(vec![Some(0), Some(1)]));
        let half = resolve_f64(&[0.5], 3).unwrap();
        assert_eq!(half, IndexSpec::At(vec![Some(0)]));
    }

    #[test]
    fn logical_recycling_and_long_subscripts() {
        assert_eq!(
            resolve_logical(&[Logical::False, Logical::True], 6),
            IndexSpec::At(vec![Some(1), Some(3), Some(5)])
        );
        assert_eq!(
            resolve_logical(&[Logical::True, Logical::True], 6),
            IndexSpec::All
        );
        assert_eq!(
            resolve_logical(&[Logical::Na], 3),
            IndexSpec::At(vec![None, None, None])
        );
        assert_eq!(
            resolve_logical(
                &[
                    Logical::False,
                    Logical::True,
                    Logical::False,
                    Logical::True,
                    Logical::True,
                    Logical::True,
                    Logical::False,
                    Logical::True,
                ],
                6,
            ),
            IndexSpec::At(vec![Some(1), Some(3), Some(4), Some(5), None])
        );
    }
}
