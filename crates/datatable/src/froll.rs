//! Exact rolling windows from data.table `src/froll.c`.
//!
//! The window is right-aligned: the first `k - 1` results are `fill`. Left and
//! center are that result shifted, which is what the C entry point does after
//! the right-aligned pass. A missing value is NaN. Variance divides by `k - 1`
//! and is clamped at 0. Fewer than two finite values is missing.

#[derive(Clone, Copy)]
pub enum Roll {
    Sum,
    Mean,
    Min,
    Max,
    Prod,
    Var,
    Sd,
    Median,
}

pub fn parse_roll(name: &str) -> Option<Roll> {
    match name {
        "sum" => Some(Roll::Sum),
        "mean" => Some(Roll::Mean),
        "min" => Some(Roll::Min),
        "max" => Some(Roll::Max),
        "prod" => Some(Roll::Prod),
        "var" => Some(Roll::Var),
        "sd" => Some(Roll::Sd),
        "median" => Some(Roll::Median),
        _ => None,
    }
}

pub fn roll_right(x: &[f64], k: usize, fill: f64, na_rm: bool, fun: Roll) -> Vec<f64> {
    let nx = x.len();
    if k == 0 || (matches!(fun, Roll::Var | Roll::Sd) && k < 2) {
        return vec![f64::NAN; nx];
    }
    let mut ans = vec![fill; nx];
    if k > nx {
        return ans;
    }
    for i in (k - 1)..nx {
        let window = &x[i + 1 - k..=i];
        ans[i] = reduce(window, na_rm, fun);
    }
    ans
}

fn reduce(window: &[f64], na_rm: bool, fun: Roll) -> f64 {
    let mut finite = Vec::with_capacity(window.len());
    for value in window {
        if value.is_nan() {
            if !na_rm {
                return f64::NAN;
            }
        } else {
            finite.push(*value);
        }
    }
    if finite.is_empty() {
        return match fun {
            Roll::Prod => 1.0,
            Roll::Mean | Roll::Sum if na_rm => f64::NAN,
            _ => f64::NAN,
        };
    }
    match fun {
        Roll::Sum => finite.iter().sum(),
        Roll::Mean => {
            let denom = if na_rm { finite.len() } else { window.len() };
            finite.iter().sum::<f64>() / denom as f64
        }
        Roll::Min => finite.iter().copied().fold(f64::INFINITY, f64::min),
        Roll::Max => finite.iter().copied().fold(f64::NEG_INFINITY, f64::max),
        Roll::Prod => finite.iter().product(),
        Roll::Var => variance(&finite),
        Roll::Sd => variance(&finite).sqrt(),
        Roll::Median => median(&mut finite),
    }
}

fn variance(values: &[f64]) -> f64 {
    if values.len() < 2 {
        return f64::NAN;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let mut sum = 0.0;
    for value in values {
        let delta = value - mean;
        sum += delta * delta;
    }
    (sum / (values.len() - 1) as f64).max(0.0)
}

fn median(values: &mut [f64]) -> f64 {
    values.sort_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal));
    let mid = values.len() / 2;
    if values.len() % 2 == 1 {
        values[mid]
    } else {
        (values[mid - 1] + values[mid]) / 2.0
    }
}
