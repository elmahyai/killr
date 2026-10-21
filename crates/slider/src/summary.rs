//! The seven summary specializations, from slider `src/summary-core.h`.
//!
//! Each one carries a state type and two fold rules: one for the leaf level,
//! which reads doubles, and one for interior nodes. `na_rm` picks between the
//! keep and drop variants. Every ordering detail matters: the folds return as
//! soon as the state turns missing, and the `na_rm` node folds deliberately do
//! not skip a missing input, so a node `NaN` from `Inf + -Inf` propagates.

use crate::longdouble::{finalize, F80};
use crate::tree::Agg;

/// R's `NA_real_`, which travels through a `long double` unchanged.
const NA_REAL_BITS: u64 = 0x7ff0_0000_0000_07a2;
/// R's `NA_LOGICAL`.
pub const NA_LGL: i32 = i32::MIN;

fn na_real() -> f64 {
    f64::from_bits(NA_REAL_BITS)
}

fn is_na(value: f64) -> bool {
    value.to_bits() == NA_REAL_BITS
}

// -----------------------------------------------------------------------------
// Sum

/// `sum_state_reset` and `sum_state_finalize` around a `long double` total.
#[derive(Clone, Copy)]
pub struct Sum {
    total: F80,
    na_rm: bool,
}

impl Sum {
    pub fn new(na_rm: bool) -> Sum {
        Sum {
            total: F80::from_f64(0.0),
            na_rm,
        }
    }

    /// The shared keep-fold tail: a missing element takes over the state.
    fn keep(&mut self, element: f64) -> bool {
        if element.is_nan() {
            self.total = F80::from_f64(element);
            return true;
        }
        self.total = self.total.add(F80::from_f64(element));
        false
    }
}

impl Agg for Sum {
    type Leaf = f64;
    type Out = f64;

    fn fold_leaves(&mut self, leaves: &[f64], begin: usize, end: usize) {
        if !self.na_rm {
            if self.total.is_nan() {
                return;
            }
            for &element in &leaves[begin..end] {
                if self.keep(element) {
                    return;
                }
            }
            return;
        }
        for &element in &leaves[begin..end] {
            if !element.is_nan() {
                self.total = self.total.add(F80::from_f64(element));
            }
        }
    }

    fn fold_nodes(&mut self, nodes: &[Sum], begin: usize, end: usize) {
        if !self.na_rm {
            if self.total.is_nan() {
                return;
            }
            for node in &nodes[begin..end] {
                if node.total.is_nan() {
                    self.total = node.total;
                    return;
                }
                self.total = self.total.add(node.total);
            }
            return;
        }
        // No missing check: a node NaN from `Inf + -Inf` must survive.
        for node in &nodes[begin..end] {
            self.total = self.total.add(node.total);
        }
    }

    fn finalize(self) -> f64 {
        finalize(self.total)
    }
}

// -----------------------------------------------------------------------------
// Product

/// A `long double` product that starts at 1.
#[derive(Clone, Copy)]
pub struct Prod {
    total: F80,
    na_rm: bool,
}

impl Prod {
    pub fn new(na_rm: bool) -> Prod {
        Prod {
            total: F80::one(),
            na_rm,
        }
    }
}

impl Agg for Prod {
    type Leaf = f64;
    type Out = f64;

    fn fold_leaves(&mut self, leaves: &[f64], begin: usize, end: usize) {
        if !self.na_rm {
            if self.total.is_nan() {
                return;
            }
            for &element in &leaves[begin..end] {
                if element.is_nan() {
                    self.total = F80::from_f64(element);
                    return;
                }
                self.total = self.total.mul(F80::from_f64(element));
            }
            return;
        }
        for &element in &leaves[begin..end] {
            if !element.is_nan() {
                self.total = self.total.mul(F80::from_f64(element));
            }
        }
    }

    fn fold_nodes(&mut self, nodes: &[Prod], begin: usize, end: usize) {
        if !self.na_rm {
            if self.total.is_nan() {
                return;
            }
            for node in &nodes[begin..end] {
                if node.total.is_nan() {
                    self.total = node.total;
                    return;
                }
                self.total = self.total.mul(node.total);
            }
            return;
        }
        for node in &nodes[begin..end] {
            self.total = self.total.mul(node.total);
        }
    }

    fn finalize(self) -> f64 {
        finalize(self.total)
    }
}

// -----------------------------------------------------------------------------
// Mean

/// `mean_state_t`: a `long double` sum and an element count.
#[derive(Clone, Copy)]
pub struct Mean {
    sum: F80,
    count: u64,
    na_rm: bool,
}

impl Mean {
    pub fn new(na_rm: bool) -> Mean {
        Mean {
            sum: F80::from_f64(0.0),
            count: 0,
            na_rm,
        }
    }
}

impl Agg for Mean {
    type Leaf = f64;
    type Out = f64;

    fn fold_leaves(&mut self, leaves: &[f64], begin: usize, end: usize) {
        if !self.na_rm {
            if self.sum.is_nan() {
                return;
            }
            for &element in &leaves[begin..end] {
                if element.is_nan() {
                    // No need to update the count; the state is already poison.
                    self.sum = F80::from_f64(element);
                    return;
                }
                self.sum = self.sum.add(F80::from_f64(element));
                self.count += 1;
            }
            return;
        }
        for &element in &leaves[begin..end] {
            if !element.is_nan() {
                self.sum = self.sum.add(F80::from_f64(element));
                self.count += 1;
            }
        }
    }

    fn fold_nodes(&mut self, nodes: &[Mean], begin: usize, end: usize) {
        if !self.na_rm {
            if self.sum.is_nan() {
                return;
            }
            for node in &nodes[begin..end] {
                if node.sum.is_nan() {
                    self.sum = node.sum;
                    return;
                }
                self.sum = self.sum.add(node.sum);
                self.count += node.count;
            }
            return;
        }
        for node in &nodes[begin..end] {
            self.sum = self.sum.add(node.sum);
            self.count += node.count;
        }
    }

    fn finalize(self) -> f64 {
        // long double division, then the double cast: R's `(double)(sum / count)`.
        let count = F80::from_f64(self.count as f64);
        finalize(self.sum.div(count))
    }
}

// -----------------------------------------------------------------------------
// Min and Max

/// `min_state_t`/`max_state_t`: a single double, compared in double.
#[derive(Clone, Copy)]
pub struct Extreme {
    value: f64,
    na_rm: bool,
    minimum: bool,
}

impl Extreme {
    pub fn min(na_rm: bool) -> Extreme {
        Extreme {
            value: f64::INFINITY,
            na_rm,
            minimum: true,
        }
    }

    pub fn max(na_rm: bool) -> Extreme {
        Extreme {
            value: f64::NEG_INFINITY,
            na_rm,
            minimum: false,
        }
    }

    fn better(&self, element: f64) -> bool {
        if self.minimum {
            element < self.value
        } else {
            element > self.value
        }
    }

    /// R's `NA` trumps `NaN` rule: `NA` stops the fold, `NaN` only marks it.
    fn keep(&mut self, element: f64) -> bool {
        if element.is_nan() {
            if is_na(element) {
                self.value = na_real();
                return true;
            }
            self.value = f64::NAN;
        } else if self.better(element) {
            self.value = element;
        }
        false
    }
}

impl Agg for Extreme {
    type Leaf = f64;
    type Out = f64;

    fn fold_leaves(&mut self, leaves: &[f64], begin: usize, end: usize) {
        if self.na_rm {
            for &element in &leaves[begin..end] {
                if self.better(element) {
                    self.value = element;
                }
            }
            return;
        }
        for &element in &leaves[begin..end] {
            if self.keep(element) {
                return;
            }
        }
    }

    /// The nodes fold is the leaves fold over the node values.
    fn fold_nodes(&mut self, nodes: &[Extreme], begin: usize, end: usize) {
        if self.na_rm {
            for node in &nodes[begin..end] {
                if self.better(node.value) {
                    self.value = node.value;
                }
            }
            return;
        }
        for node in &nodes[begin..end] {
            if self.keep(node.value) {
                return;
            }
        }
    }

    fn finalize(self) -> f64 {
        self.value
    }
}

// -----------------------------------------------------------------------------
// All and Any

/// `all_state_t`/`any_state_t`: an R logical, where `NA` is `i32::MIN`.
#[derive(Clone, Copy)]
pub struct Logic {
    value: i32,
    na_rm: bool,
    every: bool,
}

impl Logic {
    pub fn all(na_rm: bool) -> Logic {
        Logic {
            value: 1,
            na_rm,
            every: true,
        }
    }

    pub fn any(na_rm: bool) -> Logic {
        Logic {
            value: 0,
            na_rm,
            every: false,
        }
    }

    fn keep(&mut self, element: i32) -> bool {
        if self.every {
            // Already FALSE: nothing left to learn, and FALSE beats NA.
            if self.value == 0 {
                return true;
            }
            if element == 0 {
                self.value = 0;
                return true;
            }
            if element == NA_LGL {
                self.value = NA_LGL;
            }
            return false;
        }
        // Already TRUE: TRUE beats NA.
        if self.value == 1 {
            return true;
        }
        if element == 0 {
            return false;
        }
        if element == NA_LGL {
            self.value = NA_LGL;
            return false;
        }
        self.value = 1;
        true
    }

    fn drop_fold(&mut self, element: i32) -> bool {
        if self.every {
            if self.value == 0 {
                return true;
            }
            if element == 0 {
                self.value = 0;
                return true;
            }
            return false;
        }
        if self.value == 1 {
            return true;
        }
        if element == 1 {
            self.value = 1;
            return true;
        }
        false
    }
}

impl Agg for Logic {
    type Leaf = i32;
    type Out = i32;

    fn fold_leaves(&mut self, leaves: &[i32], begin: usize, end: usize) {
        for &element in &leaves[begin..end] {
            let done = if self.na_rm {
                self.drop_fold(element)
            } else {
                self.keep(element)
            };
            if done {
                return;
            }
        }
    }

    fn fold_nodes(&mut self, nodes: &[Logic], begin: usize, end: usize) {
        for node in &nodes[begin..end] {
            let done = if self.na_rm {
                self.drop_fold(node.value)
            } else {
                self.keep(node.value)
            };
            if done {
                return;
            }
        }
    }

    fn finalize(self) -> i32 {
        self.value
    }
}
