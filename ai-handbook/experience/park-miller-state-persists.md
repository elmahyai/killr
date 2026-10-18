# Park-Miller state persists across seeds

mix 1.0-13 keeps two pieces of state in its Fortran (`src/mix.f`). `rangen` keeps the
Park-Miller seed `ix`, and `gauss` keeps a second Box-Muller deviate in the saved
variable `next`, with a flag `alt`. `rngseed` (`rngs`) sets only `ix`, so the first
normal deviate after a reseed can be the cached one from an earlier call.

- Reproduced in R 4.5 and in the Python port: two `imp.mix` calls, each after
  `rngseed(777)` on the same fitted parameters, give different results. A fresh process
  gives the first result.
- So a port matches R only when the calls run in the same order from a fresh process.
  Compare a whole sequence, not one call taken from the middle of a session.
- `rangen` with no seed calls `rexit` in R. A zero generator then makes the gamma loop
  in `gamm` run forever, so the Python layer checks for a seed before any draw.
