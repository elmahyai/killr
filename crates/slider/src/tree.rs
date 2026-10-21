//! Fanout-16 segment tree, from slider `src/segment-tree.c`.
//!
//! A window aggregate is built one level at a time: the partial group at the
//! left edge, then the partial group at the right edge, then the same slice
//! one level up. The order the groups are visited is the order the values are
//! added, so it is reproduced exactly to land on R's bits.
//!
//! Interior nodes are materialized once, as `segment_tree_initialize_levels`
//! does, including nodes a window may never read, because `NaN` from
//! `Inf + -Inf` is produced at build time in R too.

pub const FANOUT: usize = 16;
pub const FANOUT_POWER: u32 = 4;

/// One node's value. `aggregate` resets it, folds groups into it, then finalizes.
pub trait Agg: Copy {
    /// The leaf type of the C specialization: `double` or `int`.
    type Leaf: Copy;
    /// The output type: R double for the numeric summaries, R integer for
    /// `all`/`any`, which store `NA_LOGICAL` rather than `NA_real_`.
    type Out: Copy;
    fn fold_leaves(&mut self, leaves: &[Self::Leaf], begin: usize, end: usize);
    fn fold_nodes(&mut self, nodes: &[Self], begin: usize, end: usize);
    fn finalize(self) -> Self::Out;
}

/// The leaves plus one vector per interior level.
pub struct Tree<A: Agg> {
    leaves: Vec<A::Leaf>,
    levels: Vec<Vec<A>>,
    /// The identity state (`nodes_initialize`) plus this query's `na_rm`.
    proto: A,
}

impl<A: Agg> Tree<A> {
    /// Build every level, grouping `FANOUT` children at a time as the C's
    /// `while (n_level_nodes > 1)` loop does.
    pub fn new(leaves: Vec<A::Leaf>, proto: A) -> Tree<A> {
        let mut n_level_nodes = leaves.len();
        let mut levels: Vec<Vec<A>> = Vec::new();

        while n_level_nodes > 1 {
            let n_next = n_level_nodes.div_ceil(FANOUT);
            let mut level = Vec::with_capacity(n_next);
            for begin in (0..n_level_nodes).step_by(FANOUT) {
                let end = (begin + FANOUT).min(n_level_nodes);
                let mut node = proto;
                match levels.last() {
                    None => node.fold_leaves(&leaves, begin, end),
                    Some(source) => node.fold_nodes(source, begin, end),
                }
                level.push(node);
            }
            levels.push(level);
            n_level_nodes = n_next;
        }

        Tree {
            leaves,
            levels,
            proto,
        }
    }

    /// Aggregate the half-open window `begin..end`.
    pub fn aggregate(&self, begin: usize, end: usize) -> A::Out {
        let mut state = self.proto;
        let mut window = Window { begin, end };

        if aggregate_leaves(&self.leaves, &mut state, &window) {
            return state.finalize();
        }
        window.advance();

        for level in &self.levels {
            if aggregate_nodes(level, &mut state, &window) {
                break;
            }
            window.advance();
        }

        state.finalize()
    }
}

/// The `begin`/`end` pair `segment_tree_aggregate_level` updates in place.
struct Window {
    begin: usize,
    end: usize,
}

impl Window {
    fn advance(&mut self) {
        let parent_begin = self.begin >> FANOUT_POWER;
        if self.begin != parent_begin * FANOUT {
            self.begin = parent_begin + 1;
        } else {
            self.begin = parent_begin;
        }
        self.end >>= FANOUT_POWER;
    }
}

/// The leaf rung. True means the window was consumed here.
fn aggregate_leaves<A: Agg>(leaves: &[A::Leaf], state: &mut A, window: &Window) -> bool {
    let parent_begin = window.begin >> FANOUT_POWER;
    let parent_end = window.end >> FANOUT_POWER;

    if parent_begin == parent_end {
        state.fold_leaves(leaves, window.begin, window.end);
        return true;
    }

    let group_begin = parent_begin * FANOUT;
    let group_end = parent_end * FANOUT;

    if window.begin != group_begin {
        state.fold_leaves(leaves, window.begin, group_begin + FANOUT);
    }
    if window.end != group_end {
        state.fold_leaves(leaves, group_end, window.end);
    }

    false
}

/// One interior rung. True means the window was consumed here.
fn aggregate_nodes<A: Agg>(source: &[A], state: &mut A, window: &Window) -> bool {
    let parent_begin = window.begin >> FANOUT_POWER;
    let parent_end = window.end >> FANOUT_POWER;

    if parent_begin == parent_end {
        state.fold_nodes(source, window.begin, window.end);
        return true;
    }

    let group_begin = parent_begin * FANOUT;
    let group_end = parent_end * FANOUT;

    if window.begin != group_begin {
        state.fold_nodes(source, window.begin, group_begin + FANOUT);
    }
    if window.end != group_end {
        state.fold_nodes(source, group_end, window.end);
    }

    false
}
