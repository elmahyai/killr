# Roadmap

killr is already a proof of concept. Packages are translated, and every finished function has a proof against R. The next work is another iteration of the same idea: finish the first round, review, raise Rust, and plug the result into existing frameworks. Nothing counts without a proof, and later rounds add more proofs.

## 1. Finish the first round

A first translation for every package that is not replaced. The prepare database already splits low-level kernels from high-level R. Free packages go to agents. A package waiting on Depends is opened after that dependency. A function is finished only when it matches R. Coverage first; the later rounds make it better.

- Screen and prioritize the rest of the catalog.
- Translate every free package.
- Prove each function against R.
- Finish the packages still in progress, and clear the functions blocked on a decision.

## 2. More review rounds

A first pass can pass its proofs and still miss an edge. Later rounds add more proofs, cover the cases the first example did not, and write the new pitfalls down so the next agents do not repeat them.

- Review every complete package again.
- Add more proofs, not only the first example.
- Resolve the proof checks that do not match R yet. Each one needs a decision: fix the translation, or record why the difference is acceptable.
- Feed what the reviews find back into `ai-handbook/experience/`.

## 3. Raise Rust coverage

More compiled kernels become Rust crates, so they run without a C or Fortran toolchain. We also decide, function by function, what should live in Rust instead of Python: the heavy numerics, the tight loops, anything that is better as a crate.

- Turn more of the Fortran and C kernels into Rust crates.
- Move more Python numerics into Rust where that is the better home.
- Measure Rust coverage on the dashboard, so progress shows up next to the function counts.

## 4. Integrate into existing frameworks

A third level after translation and review. If a translated piece already fits a mature Rust or Python library — a grid, a data frame, a chart — we integrate with that library and use it here, instead of keeping a parallel copy. The proof still compares against R.

- Look for a mature home for each translated system.
- Wrap or extend that library when the fit is real.
- Keep the R proof after the integration.

## Decisions still open

- Which big libraries stand in for R frameworks. A library that replaces a whole system needs an agreed choice before it is used.
- Which replaced packages need a second look, because their stand-in covers only part of the original.
- How the dashboard numbers are shared with outside readers, and how often the front page is refreshed.
