//! The computing C of slider 0.3.3, as a Rust crate.
//!
//! Ported from `src/segment-tree.c`, `src/summary-core.h`,
//! `src/summary-slide.c`, `src/summary-index.c`, and `src/opts-slide.h`. The R
//! glue (`vec_cast`, `vec_rank`, `vec_unrep`) stays on the Python side; what
//! lives here is the part that computes: the segment tree, the seven aggregate
//! specializations over their `na_rm` variants, and the two driving loops.
//!
//! `sum`, `prod`, and `mean` accumulate in 80-bit extended precision because
//! the C does, and that precision is visible in the result.

mod longdouble;
mod opts;
mod summary;
mod tree;

#[cfg(feature = "python")]
mod python;

pub use longdouble::F80;
pub use opts::{complete_iteration_bounds, peer_bounds, IterOpts, SlideOpts, Windows};
pub use summary::{Extreme, Logic, Mean, Prod, Sum, NA_LGL};
pub use tree::{Agg, Tree};

/// The seven summaries slider computes in C.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Sum,
    Prod,
    Mean,
    Min,
    Max,
    All,
    Any,
}

impl Kind {
    /// Whether the C specialization works on `int` leaves (`LGLSXP`) instead of
    /// `double` (`REALSXP`).
    pub fn is_logical(self) -> bool {
        matches!(self, Kind::All | Kind::Any)
    }

    pub fn from_name(name: &str) -> Option<Kind> {
        Some(match name {
            "sum" => Kind::Sum,
            "prod" => Kind::Prod,
            "mean" => Kind::Mean,
            "min" => Kind::Min,
            "max" => Kind::Max,
            "all" => Kind::All,
            "any" => Kind::Any,
            _ => return None,
        })
    }
}

/// Build the tree for a `double` summary and fill `out` for one `slide_*` call.
///
/// `out` is preallocated at `values.len()`; positions the step skips keep the
/// NaN that R's `slider_init(REALSXP, size)` leaves.
pub fn slide_dbl(kind: Kind, values: &[f64], opts: SlideOpts, na_rm: bool) -> Vec<f64> {
    let size = values.len();
    let mut out = vec![f64::NAN; size];
    let iter = IterOpts::new(opts, size as i64);

    macro_rules! run {
        ($agg:ty, $proto:expr) => {{
            let tree = Tree::<$agg>::new(values.to_vec(), $proto);
            for (position, begin, end) in Windows::new(iter) {
                out[position] = tree.aggregate(begin, end);
            }
        }};
    }

    match kind {
        Kind::Sum => run!(Sum, Sum::new(na_rm)),
        Kind::Prod => run!(Prod, Prod::new(na_rm)),
        Kind::Mean => run!(Mean, Mean::new(na_rm)),
        Kind::Min => run!(Extreme, Extreme::min(na_rm)),
        Kind::Max => run!(Extreme, Extreme::max(na_rm)),
        Kind::All | Kind::Any => unreachable!("logical kind passed to slide_dbl"),
    }

    out
}

/// Build the tree for an `all`/`any` summary and fill `out` for one `slide_*`.
///
/// Leaves are R logicals: 0, 1, or [`NA_LGL`].
pub fn slide_lgl(kind: Kind, values: &[i32], opts: SlideOpts, na_rm: bool) -> Vec<i32> {
    let size = values.len();
    // R's `slider_init()` fills a logical result with `NA_LOGICAL`, so a
    // position the step skips stays missing rather than reading as `FALSE`.
    let mut out = vec![NA_LGL; size];
    let iter = IterOpts::new(opts, size as i64);

    macro_rules! run {
        ($proto:expr) => {{
            let tree = Tree::<Logic>::new(values.to_vec(), $proto);
            for (position, begin, end) in Windows::new(iter) {
                out[position] = tree.aggregate(begin, end);
            }
        }};
    }

    match kind {
        Kind::All => run!(Logic::all(na_rm)),
        Kind::Any => run!(Logic::any(na_rm)),
        _ => unreachable!("numeric kind passed to slide_lgl"),
    }

    out
}

/// `slide_index_*` for a `double` summary.
///
/// `keys` are the dense ranks of the unique `.i` values (so they are sorted and
/// start at 1, the rank `vec_rank(ties = "dense")` gives), `peer_sizes` the
/// times each key repeats, and `starts`/`stops` the ranked window endpoints.
/// A `None` endpoint is R's `NULL`, meaning unbounded.
#[allow(clippy::too_many_arguments)]
pub fn slide_index_dbl(
    kind: Kind,
    values: &[f64],
    keys: &[i32],
    peer_sizes: &[i32],
    starts: Option<&[i32]>,
    stops: Option<&[i32]>,
    complete: bool,
    na_rm: bool,
) -> Vec<f64> {
    let mut out = vec![f64::NAN; values.len()];

    macro_rules! run {
        ($agg:ty, $proto:expr) => {{
            let tree = Tree::<$agg>::new(values.to_vec(), $proto);
            index_loop(&tree, keys, peer_sizes, starts, stops, complete, &mut out);
        }};
    }

    match kind {
        Kind::Sum => run!(Sum, Sum::new(na_rm)),
        Kind::Prod => run!(Prod, Prod::new(na_rm)),
        Kind::Mean => run!(Mean, Mean::new(na_rm)),
        Kind::Min => run!(Extreme, Extreme::min(na_rm)),
        Kind::Max => run!(Extreme, Extreme::max(na_rm)),
        Kind::All | Kind::Any => unreachable!("logical kind passed to slide_index_dbl"),
    }

    out
}

/// `slide_index_all` / `slide_index_any`.
#[allow(clippy::too_many_arguments)]
pub fn slide_index_lgl(
    kind: Kind,
    values: &[i32],
    keys: &[i32],
    peer_sizes: &[i32],
    starts: Option<&[i32]>,
    stops: Option<&[i32]>,
    complete: bool,
    na_rm: bool,
) -> Vec<i32> {
    // As in `slide_lgl`, an untouched position keeps R's `NA_LOGICAL` fill.
    let mut out = vec![NA_LGL; values.len()];

    macro_rules! run {
        ($proto:expr) => {{
            let tree = Tree::<Logic>::new(values.to_vec(), $proto);
            index_loop_i32(&tree, keys, peer_sizes, starts, stops, complete, &mut out);
        }};
    }

    match kind {
        Kind::All => run!(Logic::all(na_rm)),
        Kind::Any => run!(Logic::any(na_rm)),
        _ => unreachable!("numeric kind passed to slide_index_lgl"),
    }

    out
}

/// `SLIDE_INDEX_SUMMARY_LOOP`: one window per unique key, broadcast to peers.
fn index_loop<A: Agg<Leaf = f64, Out = f64>>(
    tree: &Tree<A>,
    keys: &[i32],
    peer_sizes: &[i32],
    starts: Option<&[i32]>,
    stops: Option<&[i32]>,
    complete: bool,
    out: &mut [f64],
) {
    let (peer_starts, peer_stops) = peer_bounds(peer_sizes);
    let (min, max) = complete_iteration_bounds(keys, starts, stops, complete);
    let mut start_cursor = 0i64;
    let mut stop_cursor = 0i64;

    for pos in min..max {
        let start_pos = opts::locate_peer_starts_pos(keys, &mut start_cursor, starts.map_or(0, |s| s[pos]), starts.is_none());
        let stop_pos = opts::locate_peer_stops_pos(keys, &mut stop_cursor, stops.map_or(0, |s| s[pos]), stops.is_none());

        let (begin, end) = if stop_pos < start_pos {
            // The window misses `.i` entirely: take a 0-slice.
            (0, 0)
        } else {
            (
                peer_starts[start_pos as usize] as usize,
                peer_stops[stop_pos as usize] as usize + 1,
            )
        };

        let result = tree.aggregate(begin, end);

        let mut element = peer_starts[pos] as usize;
        for _ in 0..peer_sizes[pos] {
            out[element] = result;
            element += 1;
        }
    }
}

/// The `int` twin of [`index_loop`].
fn index_loop_i32<A: Agg<Leaf = i32, Out = i32>>(
    tree: &Tree<A>,
    keys: &[i32],
    peer_sizes: &[i32],
    starts: Option<&[i32]>,
    stops: Option<&[i32]>,
    complete: bool,
    out: &mut [i32],
) {
    let (peer_starts, peer_stops) = peer_bounds(peer_sizes);
    let (min, max) = complete_iteration_bounds(keys, starts, stops, complete);
    let mut start_cursor = 0i64;
    let mut stop_cursor = 0i64;

    for pos in min..max {
        let start_pos = opts::locate_peer_starts_pos(keys, &mut start_cursor, starts.map_or(0, |s| s[pos]), starts.is_none());
        let stop_pos = opts::locate_peer_stops_pos(keys, &mut stop_cursor, stops.map_or(0, |s| s[pos]), stops.is_none());

        let (begin, end) = if stop_pos < start_pos {
            (0, 0)
        } else {
            (
                peer_starts[start_pos as usize] as usize,
                peer_stops[stop_pos as usize] as usize + 1,
            )
        };

        let result = tree.aggregate(begin, end);

        let mut element = peer_starts[pos] as usize;
        for _ in 0..peer_sizes[pos] {
            out[element] = result;
            element += 1;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn opts(before: i64, after: i64, step: i64, complete: bool) -> SlideOpts {
        SlideOpts::new(before, false, after, false, step, complete)
    }

    #[test]
    fn slide_sum_matches_r_smoke() {
        // slide_sum(x, before = 2, after = 1, step = 2, complete = TRUE)
        let out = slide_dbl(Kind::Sum, &[1.0, 5.0, 3.0, 2.0, 6.0, 10.0], opts(2, 1, 2, true), false);
        assert!(out[0].is_nan() && out[1].is_nan());
        assert_eq!(out[2], 11.0);
        assert!(out[3].is_nan());
        assert_eq!(out[4], 21.0);
        assert!(out[5].is_nan());
    }

    #[test]
    fn slide_index_sum_matches_r_smoke() {
        // slide_index_sum(x, i, before = 2) with i = 0, 1, 3, 4, 6, 8
        // i = 0, 1, 3, 4, 6, 8 with .before = 2 and .after = 0. R ranks i and
        // i - 2 together (`vec_rank(ties = "dense")`), so over
        // {-2, -1, 0, 1, 2, 3, 4, 6, 8} the keys are 3, 4, 6, 7, 8, 9 and the
        // starts 1, 2, 4, 5, 7, 8.
        let keys = [3, 4, 6, 7, 8, 9];
        let peer_sizes = [1, 1, 1, 1, 1, 1];
        let starts = [1, 2, 4, 5, 7, 8];
        let stops = [3, 4, 6, 7, 8, 9];
        let out = slide_index_dbl(
            Kind::Sum,
            &[1.0, 5.0, 3.0, 2.0, 6.0, 10.0],
            &keys,
            &peer_sizes,
            Some(&starts),
            Some(&stops),
            false,
            false,
        );
        assert_eq!(out, vec![1.0, 6.0, 8.0, 5.0, 8.0, 16.0]);
    }

    #[test]
    fn mean_of_empty_window_is_nan() {
        let out = slide_dbl(Kind::Mean, &[1.0, 2.0, 3.0], opts(i64::MAX, -1, 1, false), false);
        assert!(out[0].is_nan());
        assert_eq!(out[1], 1.0);
        assert_eq!(out[2], 1.5);
    }

    #[test]
    fn empty_windows_keep_the_identity() {
        let out = slide_dbl(Kind::Min, &[1.0, 2.0, 3.0], opts(i64::MAX, -1, 1, false), false);
        assert_eq!(out[0], f64::INFINITY);
        let out = slide_dbl(Kind::Max, &[1.0, 2.0, 3.0], opts(i64::MAX, -1, 1, false), false);
        assert_eq!(out[0], f64::NEG_INFINITY);
        let out = slide_dbl(Kind::Sum, &[1.0, 2.0, 3.0], opts(i64::MAX, -1, 1, false), false);
        assert_eq!(out[0], 0.0);
        let out = slide_dbl(Kind::Prod, &[1.0, 2.0, 3.0], opts(i64::MAX, -1, 1, false), false);
        assert_eq!(out[0], 1.0);
    }

    #[test]
    fn nan_propagates_unless_na_rm() {
        let values = [1.0, f64::NAN, 2.0];
        let out = slide_dbl(Kind::Sum, &values, opts(1, 0, 1, false), false);
        assert!(out[1].is_nan());
        let out = slide_dbl(Kind::Sum, &values, opts(1, 0, 1, false), true);
        assert_eq!(out[1], 1.0);
    }

    #[test]
    fn na_beats_nan_in_min() {
        let na = f64::from_bits(0x7ff0_0000_0000_07a2);
        let values = [f64::NAN, na, 2.0];
        let out = slide_dbl(Kind::Min, &values, opts(1, 0, 1, false), false);
        // R's slide_min(c(NaN), before = 0) is 0x7ff8000000000000 and
        // slide_min(c(1, NA), before = 1)[2] is 0x7ff00000000007a2.
        assert_eq!(out[0].to_bits(), 0x7ff8_0000_0000_0000, "NaN stays NaN");
        assert_eq!(out[1].to_bits(), 0x7ff0_0000_0000_07a2, "NA stays NA");
    }

    #[test]
    fn logic_tracks_na() {
        let out = slide_lgl(Kind::All, &[1, NA_LGL, 0], opts(2, 0, 1, false), false);
        // Window at 0 is just TRUE.
        assert_eq!(out[0], 1);
        // Window at 1 is TRUE, NA -> NA.
        assert_eq!(out[1], NA_LGL);
        // Window at 2 has a FALSE, which wins over NA.
        assert_eq!(out[2], 0);
    }

    #[test]
    fn any_true_beats_na() {
        let out = slide_lgl(Kind::Any, &[1, NA_LGL, 0], opts(2, 0, 1, false), false);
        assert_eq!(out[0], 1);
        assert_eq!(out[1], 1);
        assert_eq!(out[2], 1);
        let out = slide_lgl(Kind::Any, &[NA_LGL, 0], opts(1, 0, 1, false), false);
        assert_eq!(out[0], NA_LGL);
        assert_eq!(out[1], NA_LGL);
    }

    #[test]
    fn skipped_positions_stay_na() {
        // R: slide_all(c(TRUE, FALSE, NA, TRUE, NA, FALSE), before = 0, step = 2)
        // is `TRUE NA NA NA NA NA`, so the step leaves `NA_LOGICAL`, not `FALSE`.
        let values = [1, 0, NA_LGL, 1, NA_LGL, 0];
        let out = slide_lgl(Kind::All, &values, opts(0, 0, 2, false), false);
        assert_eq!(out, vec![1, NA_LGL, NA_LGL, NA_LGL, NA_LGL, NA_LGL]);
        let out = slide_lgl(Kind::Any, &values, opts(0, 0, 2, false), false);
        assert_eq!(out, vec![1, NA_LGL, NA_LGL, NA_LGL, NA_LGL, NA_LGL]);
    }

    #[test]
    fn index_skipped_positions_stay_na() {
        // R: slide_index_all(c(TRUE, FALSE, TRUE), c(1, 2, 5), before = 3,
        // complete = TRUE) is `NA NA FALSE`, because the first two windows are
        // partial. `complete = FALSE` computes them instead: `TRUE FALSE FALSE`.
        // Dense ranks for `i = 1:3` and `starts = i - 3` are `4:6` and `1:3`.
        let values = [1, 0, 1];
        let keys = [4, 5, 6];
        let starts = [1, 2, 3];
        let stops = keys;
        let peers = [1, 1, 1];
        let out = slide_index_lgl(
            Kind::All, &values, &keys, &peers, Some(&starts), Some(&stops), true, false,
        );
        assert_eq!(out, vec![NA_LGL, NA_LGL, NA_LGL]);
        let out = slide_index_lgl(
            Kind::All, &values, &keys, &peers, Some(&starts), Some(&stops), false, false,
        );
        assert_eq!(out, vec![1, 0, 0]);
    }
}
