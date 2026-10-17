//! Product via `sum(log(abs(x)))`, from `productExpSumLog_lowlevel_template.h`.
//!
//! The R wrapper calls `.Call(C_productExpSumLog, x, idxs, na.rm, TRUE)`.
//! `TRUE` is `hasNA`. The low-level loop always inspects missing values; an
//! empty selection returns `exp(0) = 1`.

use crate::indices::{resolve, Idxs, IndexError, Selection};

/// Bit pattern of R's `NA_real_`.
pub const R_NA_BITS: u64 = 0x7ff0_0000_0000_07a2;

/// R's missing real value.
pub fn r_na() -> f64 {
    f64::from_bits(R_NA_BITS)
}

#[derive(Clone, Copy)]
enum Obs {
    Value(f64),
    Missing,
}

/// Product of a real vector. `idxs` follows matrixStats index rules.
pub fn product(x: &[f64], idxs: Idxs<'_>, na_rm: bool) -> Result<f64, IndexError> {
    let selection = resolve(idxs, x.len(), true)?;
    Ok(accumulate_selected(x, false, selection, na_rm))
}

/// Product of an integer vector. `NA_integer_` is a missing value, and any
/// zero forces a positive zero, which is the integer branch of the template.
pub fn product_integers(x: &[i64], idxs: Idxs<'_>, na_rm: bool) -> Result<f64, IndexError> {
    let selection = resolve(idxs, x.len(), true)?;
    Ok(accumulate_selected(x, true, selection, na_rm))
}

fn accumulate_selected<T>(values: &[T], integer: bool, selection: Selection, na_rm: bool) -> f64
where
    T: Copy + Into<Value>,
{
    let fetch = |pos: usize| -> Obs {
        match values.get(pos) {
            Some(&value) => value.into().obs(integer),
            None => Obs::Missing,
        }
    };
    match selection {
        Selection::All => accumulate((0..values.len()).map(fetch), integer, na_rm),
        Selection::Pick(picked) => accumulate(
            picked.into_iter().map(|slot| match slot {
                Some(pos) => fetch(pos),
                None => Obs::Missing,
            }),
            integer,
            na_rm,
        ),
    }
}

struct Value(f64, bool);

impl From<f64> for Value {
    fn from(value: f64) -> Self {
        Self(value, false)
    }
}

impl From<i64> for Value {
    fn from(value: i64) -> Self {
        Self(value as f64, value == crate::indices::NA_INTEGER)
    }
}

impl Value {
    fn obs(self, integer: bool) -> Obs {
        if integer && self.1 {
            Obs::Missing
        } else if self.0.is_nan() {
            Obs::Missing
        } else {
            Obs::Value(self.0)
        }
    }
}

fn accumulate(obs: impl Iterator<Item = Obs>, integer: bool, na_rm: bool) -> f64 {
    let mut y = 0.0f64;
    let mut isneg = false;
    let mut has_zero = false;

    for (ii, item) in obs.enumerate() {
        let mut t = match item {
            Obs::Missing => {
                if na_rm {
                    continue;
                }
                if integer {
                    return r_na();
                }
                f64::NAN
            }
            Obs::Value(value) => value,
        };

        if integer {
            if t < 0.0 {
                isneg = !isneg;
                t = -t;
            } else if t == 0.0 {
                has_zero = true;
                if na_rm {
                    break;
                }
            }
            y += t.ln();
        } else {
            if t < 0.0 {
                isneg = !isneg;
                t = -t;
            }
            y += t.ln();
            if ii % 1_048_576 == 0 && y.is_nan() {
                break;
            }
        }
    }

    if y.is_nan() {
        return r_na();
    }
    if integer && has_zero {
        return 0.0;
    }

    let mut out = y.exp();
    if isneg {
        out = -out;
    }
    if out > f64::MAX {
        f64::INFINITY
    } else if out < -f64::MAX {
        f64::NEG_INFINITY
    } else {
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::indices::Idxs;

    fn all(x: &[f64]) -> f64 {
        product(x, Idxs::All, false).unwrap()
    }

    fn close(actual: f64, expected: f64) {
        assert!(
            (actual - expected).abs() < 1e-8,
            "{actual} differs from {expected}"
        );
    }

    fn is_na(value: f64) -> bool {
        value.to_bits() == R_NA_BITS
    }

    #[test]
    fn empty_product_is_one() {
        assert_eq!(all(&[]), 1.0);
        assert_eq!(product(&[], Idxs::Integer(&[]), false).unwrap(), 1.0);
    }

    #[test]
    fn negatives_and_exact_small_product() {
        let value = all(&[1.0, -4.0, 2.0]);
        assert!((value - (-8.0)).abs() < 1e-8);
        assert!(value.is_sign_negative());
    }

    #[test]
    fn real_zero_keeps_the_sign() {
        let value = all(&[-1.0, 0.0]);
        assert_eq!(value, 0.0);
        assert!(value.is_sign_negative());
        let flipped = all(&[0.0, -1.0]);
        assert!(flipped.is_sign_negative());
    }

    #[test]
    fn integer_zero_is_positive() {
        let value = product_integers(&[-1, 0], Idxs::All, false).unwrap();
        assert_eq!(value, 0.0);
        assert!(value.is_sign_positive());
        let with_na = product_integers(&[0, i64::from(i32::MIN)], Idxs::All, false).unwrap();
        assert!(is_na(with_na));
    }

    #[test]
    fn missing_values_follow_na_rm() {
        assert!(is_na(all(&[1.0, f64::NAN, 2.0])));
        assert!(is_na(all(&[1.0, r_na(), 2.0])));
        let dropped = product(&[1.0, f64::NAN, 2.0], Idxs::All, true).unwrap();
        assert!((dropped - 2.0).abs() < 1e-12);
        assert_eq!(
            product(&[f64::NAN, f64::NAN], Idxs::All, true).unwrap(),
            1.0
        );
    }

    #[test]
    fn zero_times_infinity_is_missing() {
        assert!(is_na(all(&[0.0, f64::INFINITY])));
        assert!(is_na(
            product(&[0.0, f64::INFINITY], Idxs::All, true).unwrap()
        ));
        assert_eq!(all(&[2.0, f64::INFINITY]), f64::INFINITY);
        assert_eq!(all(&[2.0, f64::NEG_INFINITY]), f64::NEG_INFINITY);
    }

    #[test]
    fn overflow_and_indexes() {
        assert_eq!(all(&[1e200, 1e200, 1e200]), f64::INFINITY);
        assert_eq!(all(&[-1e200, 1e200, 1e200]), f64::NEG_INFINITY);
        let x = [10.0, 20.0, 30.0, 40.0];
        close(all(&x), 240_000.0);
        close(product(&x, Idxs::Integer(&[1, 3]), false).unwrap(), 300.0);
        assert_eq!(product(&x, Idxs::Integer(&[0]), false).unwrap(), 1.0);
        close(
            product(&x, Idxs::Integer(&[-1, -2]), false).unwrap(),
            1_200.0,
        );
        assert!(is_na(product(&x, Idxs::Integer(&[1, 9]), false).unwrap()));
        close(product(&x, Idxs::Integer(&[1, 9]), true).unwrap(), 10.0);
        assert_eq!(product(&x, Idxs::Integer(&[]), false).unwrap(), 1.0);
        close(product(&x, Idxs::Real(&[0.5]), false).unwrap(), 10.0);
        close(product(&x, Idxs::Real(&[1.9, 3.1]), false).unwrap(), 300.0);
        close(
            product(&x, Idxs::Real(&[-1.2, -3.9]), false).unwrap(),
            800.0,
        );
        close(
            product(&x, Idxs::Integer(&[2, 2, 1]), false).unwrap(),
            4_000.0,
        );
        close(
            product(&x, Idxs::Logical(&[1, 0, 1, 0]), false).unwrap(),
            300.0,
        );
        close(product(&x, Idxs::Logical(&[1, 0]), false).unwrap(), 300.0);
        assert_eq!(product(&x, Idxs::Logical(&[0]), false).unwrap(), 1.0);
        close(product(&x, Idxs::Logical(&[1]), false).unwrap(), 240_000.0);
        assert!(is_na(
            product(&x, Idxs::Logical(&[1, -1, 0, 1]), false).unwrap()
        ));
        let err = product(&x, Idxs::Integer(&[1, -2]), false).unwrap_err();
        assert_eq!(
            err.message,
            "only 0's may be mixed with negative subscripts"
        );
        let err = product(&x, Idxs::Real(&[f64::NEG_INFINITY, -1.0]), false).unwrap_err();
        assert_eq!(
            err.message,
            "only 0's may be mixed with negative subscripts"
        );
    }

    #[test]
    fn short_vector_with_zero_negative_and_na() {
        let x = [0.0, -2.0, f64::NAN];
        assert!(is_na(all(&x)));
        let kept = product(&x, Idxs::All, true).unwrap();
        assert_eq!(kept, 0.0);
        assert!(kept.is_sign_negative());
    }
}
