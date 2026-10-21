# Timings Are Measured, Not Estimated

A `check.r_ms` and `check.translated_ms` that both end in two decimals are a guess, not a
reading. `median()` of twenty `Sys.time()` differences gives values like
`1.6843080520629883`, and `statistics.median` of twenty `perf_counter` differences gives
values like `7.737481500953436`. When a record shows `1.65` and `6.92`, the pair was
written by hand to describe the shape of the result, and the `speedup` derived from it is
invented too.

This matters because `speedup` is a claim about the port, and it is the only part of a
record that no value comparison can contradict: `matches` and `max_abs_diff` are checked
against R, but a fabricated pair passes every check the constitution names. Eleven
`slide_period`/`pslide_period` records carried such a pair. Re-running the same two proof
scripts replaced them with real readings, and every one still matched at `diff = 0`; only
the numbers on the page changed, in one case from a reported `0.35x` to `0.23x`.

Two consequences for a finished package:

- A record is not finished because its proof is finished. Re-run the pair, then write what
  the pair printed.
- Re-run from the scripts under `proof/`, never from a shell one-liner that re-derives the
  case. The case in the record has to be the case in the files, or the timing describes
  work that was not the proof.

A `speedup` below `1` is not an error. The `slide_sum` family measures `~0.02 ms` per call,
where Python's `perf_counter` overhead and one NumPy-to-`Vec<f64>` copy are most of the
time and the segment tree has nothing to amortise. The `slide_index_*` summaries, which do
real index work per call, come out `10x` to `25x` faster. Report both.
