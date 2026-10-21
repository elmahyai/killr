//! `struct slide_opts` / `struct iter_opts`, from slider `src/opts-slide.h`.
//!
//! The options are already validated on the Python side, which raises the same
//! messages as R. This module keeps the two facts the C derives from them: the
//! sign of each bound (which decides whether `complete` trims the iteration and
//! whether a direction is unbounded) and the start/stop walk the summary loop
//! performs.

/// What `slider_sum`'s `.before`/`.after`/`.step`/`.complete` become in C.
#[derive(Clone, Copy)]
pub struct SlideOpts {
    pub before: i64,
    pub before_unbounded: bool,
    pub before_positive: bool,
    pub after: i64,
    pub after_unbounded: bool,
    pub after_positive: bool,
    pub step: i64,
    pub complete: bool,
}

impl SlideOpts {
    pub fn new(
        before: i64,
        before_unbounded: bool,
        after: i64,
        after_unbounded: bool,
        step: i64,
        complete: bool,
    ) -> SlideOpts {
        SlideOpts {
            before,
            before_unbounded,
            before_positive: before >= 0,
            after,
            after_unbounded,
            after_positive: after >= 0,
            step,
            complete,
        }
    }
}

/// The unwound iteration: which output positions to fill and the window bounds
/// each one starts from.
#[derive(Clone, Copy)]
pub struct IterOpts {
    pub iter_min: i64,
    pub iter_max: i64,
    pub iter_step: i64,
    pub start: i64,
    pub start_step: i64,
    pub stop: i64,
    pub stop_step: i64,
    pub size: i64,
}

impl IterOpts {
    pub fn new(opts: SlideOpts, size: i64) -> IterOpts {
        let mut iter_min = 0;
        let mut iter_max = size;

        if opts.complete {
            if opts.before_positive {
                iter_min += opts.before;
            }
            if opts.after_positive {
                iter_max -= opts.after;
            }
        }

        // Forward adjustment, so a `complete` window keeps its size.
        let offset = if opts.complete && opts.before_positive {
            opts.before
        } else {
            0
        };

        let (start, start_step) = if opts.before_unbounded {
            (0, 0)
        } else {
            (offset - opts.before, opts.step)
        };
        let (stop, stop_step) = if opts.after_unbounded {
            (size - 1, 0)
        } else {
            (offset + opts.after, opts.step)
        };

        IterOpts {
            iter_min,
            iter_max,
            iter_step: opts.step,
            start,
            start_step,
            stop,
            stop_step,
            size,
        }
    }
}

/// One iteration's half-open element range, `begin..end`.
///
/// A window that misses the vector entirely becomes `0..0`, the empty slice
/// `SLIDE_SUMMARY_LOOP` substitutes.
pub struct Windows {
    iter: IterOpts,
    index: i64,
    start: i64,
    stop: i64,
}

impl Windows {
    pub fn new(iter: IterOpts) -> Windows {
        Windows {
            iter,
            index: iter.iter_min,
            start: iter.start,
            stop: iter.stop,
        }
    }
}

impl Iterator for Windows {
    /// `(output position, begin, end)` with `begin == end` for an empty window.
    type Item = (usize, usize, usize);

    fn next(&mut self) -> Option<(usize, usize, usize)> {
        if self.index >= self.iter.iter_max {
            return None;
        }

        let mut begin = self.start.max(0);
        let mut end = (self.stop + 1).min(self.iter.size);
        if end < begin {
            begin = 0;
            end = 0;
        }

        let position = self.index;
        self.index += self.iter.iter_step;
        self.start += self.iter.start_step;
        self.stop += self.iter.stop_step;

        Some((position as usize, begin as usize, end as usize))
    }
}

/// `fill_peer_info`: the first and last element position of each index peer.
pub fn peer_bounds(peer_sizes: &[i32]) -> (Vec<i32>, Vec<i32>) {
    let mut starts = Vec::with_capacity(peer_sizes.len());
    let mut stops = Vec::with_capacity(peer_sizes.len());
    let mut cursor = 0i32;
    for &size in peer_sizes {
        starts.push(cursor);
        stops.push(cursor + size - 1);
        cursor += size;
    }
    (starts, stops)
}

/// `compute_from`, slider `src/slide-period.c`: the first peer that is inside a
/// `complete` window.
///
/// `keys` are the dense ranks of `i`, `starts` those of the first window's
/// `.before` endpoint, and `n` their size.
pub fn compute_from(starts: &[i32], first: i32, n: usize, before_unbounded: bool) -> i32 {
    if before_unbounded {
        return 1;
    }
    let mut from = 1;
    for &start in starts.iter().take(n) {
        if first > start {
            from += 1;
        } else {
            break;
        }
    }
    from
}

/// `compute_to`, the mirror of [`compute_from`] for `.after`.
pub fn compute_to(stops: &[i32], last: i32, n: usize, after_unbounded: bool) -> i32 {
    if after_unbounded {
        return n as i32;
    }
    let mut to = n as i32;
    for &stop in stops.iter().take(n).rev() {
        if last < stop {
            to -= 1;
        } else {
            break;
        }
    }
    to
}

/// `compute_min_iteration` / `compute_max_iteration`, 0-based.
///
/// R's `compute_from` is 1-based, so the first loop position is `from - 1` and
/// the loop stays under `to`.
pub fn complete_iteration_bounds(
    keys: &[i32],
    starts: Option<&[i32]>,
    stops: Option<&[i32]>,
    complete: bool,
) -> (usize, usize) {
    if !complete || keys.is_empty() {
        return (0, keys.len());
    }
    let first = keys[0];
    let last = keys[keys.len() - 1];
    let from = match starts {
        Some(starts) => compute_from(starts, first, keys.len(), false),
        None => 1,
    };
    let to = match stops {
        Some(stops) => compute_to(stops, last, keys.len(), false),
        None => keys.len() as i32,
    };
    let min = (from - 1).max(0) as usize;
    let max = to.max(0) as usize;
    (min.min(keys.len()), max.min(keys.len()))
}

/// `locate_peer_starts_pos`: the first peer whose key is not below `target`.
///
/// The cursor only moves forward, as `struct index_info` keeps it across the
/// loop; `last_pos + 1` signals "past the end", which the caller reads as an
/// out-of-bounds window.
pub fn locate_peer_starts_pos(keys: &[i32], cursor: &mut i64, target: i32, unbounded: bool) -> i64 {
    if unbounded {
        return 0;
    }
    let last = keys.len() as i64 - 1;
    if *cursor > last {
        return last + 1;
    }
    while keys[*cursor as usize] < target {
        *cursor += 1;
        if *cursor > last {
            return last + 1;
        }
    }
    *cursor
}

/// `locate_peer_stops_pos`: the last peer whose key is not above `target`.
pub fn locate_peer_stops_pos(keys: &[i32], cursor: &mut i64, target: i32, unbounded: bool) -> i64 {
    if unbounded {
        return keys.len() as i64 - 1;
    }
    let last = keys.len() as i64 - 1;
    if *cursor > last {
        return last;
    }
    while keys[*cursor as usize] <= target {
        *cursor += 1;
        if *cursor > last {
            return last;
        }
    }
    *cursor - 1
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn windows_clip_partial_and_zero_misses() {
        let opts = SlideOpts::new(2, false, 1, false, 2, true);
        let windows: Vec<_> = Windows::new(IterOpts::new(opts, 6)).collect();
        // slide_sum(x, before = 2, after = 1, step = 2, complete = TRUE) on six
        // elements fills positions 2 and 4 from x[0..4] and x[2..6].
        assert_eq!(windows, vec![(2, 0, 4), (4, 2, 6)]);
    }

    #[test]
    fn unbounded_before_pins_the_start() {
        let opts = SlideOpts::new(i64::MAX, true, -1, false, 1, false);
        let windows: Vec<_> = Windows::new(IterOpts::new(opts, 3)).collect();
        assert_eq!(windows, vec![(0, 0, 0), (1, 0, 1), (2, 0, 2)]);
    }

    #[test]
    fn peer_bounds_are_cumulative() {
        let (starts, stops) = peer_bounds(&[2, 1, 3]);
        assert_eq!(starts, vec![0, 2, 3]);
        assert_eq!(stops, vec![1, 2, 5]);
    }

    #[test]
    fn complete_bounds_trim_both_edges() {
        // keys 1,2,3; starts 0,1,2; stops 2,3,4 with complete = TRUE.
        let (min, max) = complete_iteration_bounds(&[1, 2, 3], Some(&[0, 1, 2]), Some(&[2, 3, 4]), true);
        assert_eq!((min, max), (1, 2));
    }

    #[test]
    fn locate_walks_forward_only() {
        let keys = [1, 3, 5, 7];
        let mut cursor = 0;
        assert_eq!(locate_peer_starts_pos(&keys, &mut cursor, 3, false), 1);
        assert_eq!(cursor, 1);
        assert_eq!(locate_peer_starts_pos(&keys, &mut cursor, 9, false), 4);
        let mut cursor = 0;
        assert_eq!(locate_peer_stops_pos(&keys, &mut cursor, 3, false), 1);
        assert_eq!(locate_peer_stops_pos(&keys, &mut cursor, 0, false), 1);
    }
}
