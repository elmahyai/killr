# Roadmap

killr is a proof of concept. The agents produce translations fast, but a first translation is not a finished one. This page lists what is still to do.

## More review rounds

- Review every complete package again. A first pass can pass its proofs and still miss an edge case, so later rounds look at the cases the first pass did not cover.
- Check the 7 proof checks that do not match R yet (out of 6,006 recorded). Each one needs a decision: fix the translation, or record why the difference is acceptable.
- Finish the 14 packages still in progress.
- Feed what the reviews find back into `experience/`, so the next agents avoid the same mistakes.

## Raise Rust coverage

- Turn more of the Fortran and C kernels into Rust crates. Today there are 132 crates.
- Measure Rust coverage on the dashboard, so progress shows up next to the function counts.
- Move the heavy numerics off the C and Fortran toolchains where a Rust kernel is ready.

## Decisions still open

- Which big libraries stand in for R frameworks. A library that replaces a whole system needs an agreed choice before it is used.
- Which of the 38 replaced packages need a second look, because their stand-in covers only part of the original.
- How the dashboard numbers are shared with outside readers, and how often the front page is refreshed.
