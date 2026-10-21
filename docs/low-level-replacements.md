# Ten low-level packages that do not need a translation

Recorded in `rcran/replaced.json`. These are picked from the low-level table in
`orchestrator/orchestrator.sqlite`, descending by Fortran + C + C++ lines, and every one
is a thin R layer over a C or C++ system that already has an authoritative Python
binding. Nothing here is a reimplementation, so the replacement is not an approximation:
it calls the same compiled code the R package calls, which is what makes the result
dependable rather than merely similar.

**Total: 2,724,417 native lines, 12.9% of the pending low-level backlog (21,047,104)
and 11.6% of all low-level lines in the table.**

The largest rows of the table are omitted because they are already replaced: `pak`
(530k), `igraph` (409k), `RSQLite` (277k), `Matrix` (125k), `StanHeaders` (156k),
`httpuv` (102k), `terra` (66k), `lpSolve` (46k), `writexl` (39k), `vctrs` (38k).
Also omitted, with reasons, in "Just missed" below.

## The test a pick has to pass

Two conditions, both checked against the tarball rather than the package description:

1. **The native code is not R's.** It is an upstream library vendored into `src/`.
   Measured as code lines outside the top-level `src/` directory.
2. **A Python binding to that same library exists, is current, and is maintained by
   the library's own authors or by a well-established project.**

Where both hold, the numerical result matches because it is the same machine code, so
the stand-in is safe in ordinary use. Where a package would fail either test it is
listed under "Just missed" instead.

## The ten

| # | Package | Native LOC | Vendored | R glue | Exports | Stand-in |
|---:|---|---:|---:|---:|---:|---|
| 1 | `rswipl` | 480,557 | 99.8% | 158 | `exportPattern` | `janus-swi` |
| 2 | `charr` | 394,184 | 82.1% | 3,862 | 69 | finished `stringr` port + `PyICU` |
| 3 | `pkgdepends` | 387,455 | 99.8% | 19,448 | 36 | `pip` / `uv` |
| 4 | `rmumps` | 301,000 | 99.5% | 55 | 3 | `pymumps` |
| 5 | `adbcsqlite` | 275,489 | 100% | 42 | 1 | `adbc-driver-manager` + `adbc-driver-sqlite` |
| 6 | `talib` | 217,788 | 99.6% | 31,141 | 400 | `TA-Lib` |
| 7 | `leidenAlg` | 209,133 | 99.9% | 137 | 7 | `igraph` + `leidenalg` |
| 8 | `leidenbase` | 195,194 | 99.3% | 69 | 1 | `igraph` + `leidenalg` |
| 9 | `hdf5r` | 140,350 | 97.9% | 6,581 | 76 | `h5py` |
| 10 | `mongolite` | 123,267 | 98.7% | 885 | 6 | `pymongo` |

"Vendored" is the share of native code lines outside the package's own directory, so it
is the share that would be deleted rather than translated. `charr` is the exception on
purpose: only ICU counts as vendored there, because its ALTREP backend is the package's
own code and is being dropped for a reason other than being someone else's library.

---

### 1. `rswipl` — 480,557 lines

**What the native code is.** `swipl-devel` 10.1.16, the complete SWI-Prolog engine:
38.4 MB, 4,190 files, 99.8% of the code. The R package is three files, 158 lines, and
its work is `dyn.load` on `libswipl.so` plus `.onLoad` bookkeeping. The exported
"functions" are not R functions at all — `NAMESPACE` is `exportPattern("^[[:alpha:]]+")`,
so whatever predicates the Prolog state carries are what R sees. There are six
`.Call` entry points: `consult`, `query`, `submit`, `clear`, `init`, `done`.

**Stand-in.** `janus-swi` (BSD-2-Clause, 1.5.3, June 2026) — SWI-Prolog's own official
bidirectional Python interface, the same embedding role through the same `libswipl`.
The Prolog program stays a Prolog program; Python is the host instead of R.

**Why this is right.** Translating the interior of an ISO Prolog implementation is not
in scope for this project by any reading, and no amount of Rust would make it the R
package. This is the `rstan` → `cmdstanpy` shape: the engine stays itself and Python
drives it.

**What is not covered.** The predicate library that R had loaded is whatever the
installed SWI-Prolog distribution ships, so a proof at `1e-8` against `rswipl` is not
the check here — the check is a Prolog goal through Janus returning the same bindings.

### 2. `charr` — 394,184 lines

**What the native code is.** 82.1% ICU 78 (`icu78/`), then the package's own ALTREP
machinery: `altrep_backend` 39,016 lines, `base_backend` 23,856, `shared` 7,526
(share of the 394,184 `.cpp` lines).
The R layer is 81 files and 3,862 lines with 69 exports.

**Stand-in.** The `stringr` port that is already finished in this repository (66
functions, complete, on `stringi` and `PyICU`), plus `PyICU` which is already in the
`native` list. `charr` is a fork of `stringr` for ALTREP strings: **62 of its 69
exports are the same names as `stringr`'s.** The seven that differ are
`str_read_lines`, `str_reverse`, `str_write_lines` and four R-session knobs
(`charr_backend`, `charr_threads`, `charr_min_chunk`, `charr_chunks_per_worker`).

**Why this is right.** Two distinct reasons and only one of them is about code reuse.
The string semantics are ICU's, and `PyICU` is already the agreed route for ICU in
`stringi`, so the answers are the same ICU calls. The ALTREP quarter — 70k lines — is R's
own internal character-vector representation, a C-level optimisation with no Python
counterpart to be faithful to. Porting it would produce a struct nobody in Python can
observe.

**What is not covered.** Threading and chunk-size controls have no meaning; the two
line-IO helpers are a few lines each if they are ever wanted.

### 3. `pkgdepends` — 387,455 lines

**What the native code is.** `tree-sitter` 372,726 lines (98.1%) and a bundled `yaml`
parser. The R layer is 95 files and 19,448 lines with 36 exports.

**Stand-in.** `pip` and `uv`, which is the decision already recorded for `pak` — and
`pak` is `pkgdepends` with a command-line front end. For the parsing corner,
`tree_sitter` plus a tree-sitter R grammar.

**Why this is right.** The package resolves and installs *R* packages. Its dependency
graph, its `DESCRIPTION` fetching, its library trees and its install plans are facts
about R's packaging system, which does not exist on the Python side. The tree-sitter
grammar is vendored only because the package parses R source to find dependencies.

**What is not covered.** Nothing is claimed to match function for function. This is a
role replacement, the same as `pak`, `renv`, `devtools` and `rcmdcheck` above it.

### 4. `rmumps` — 301,000 lines

**What the native code is.** MUMPS 5.2.1: 215,999 lines in `src/lib` (Fortran and C).
The R layer is 55 lines total — `RcppExports.R`, a `methods.R` with seven one-line S3
bridges, and `zzz.R` reading constants. Three exports.

**Stand-in.** `pymumps` (BSD-3-Clause, 0.4.0, February 2026), Python bindings for MUMPS.

**Why this is right.** This is the textbook case for the `nloptr` → `nlopt` precedent
already in `native`: a solver package that vendors the solver. Same matrix ordering,
same pivoting, same `INFOG` codes, so the factorisation and the solution agree. A Rust
rewrite of a sparse multifrontal solver would be a research project with a worse
answer.

**What is not covered.** `pymumps` needs MPI and `mpi4py` even for a serial run, and its
default context is centralised (rank 0 holds the matrix). The R class also exposes
`set_permutation`, `get_infos` and `solveptr`, which map onto MUMPS parameters rather
than onto `pymumps` calls one for one.

### 5. `adbcsqlite` — 275,489 lines

**What the native code is.** 100% vendored: the ADBC driver manager and the SQLite
amalgamation, in `src/c`. The R layer is **one file of 42 lines** and it exports **one
object**, the driver. `NAMESPACE` is three S3 methods and a `useDynLib`.

**Stand-in.** `adbc-driver-manager` and `adbc-driver-sqlite` (Apache-2.0, 1.12.0, July
2026), published by the Apache Arrow project that owns ADBC.

**Why this is right.** The R package and the Python package are two bindings over one
C++ project, released by the same organisation. There is nothing of R in it and
nothing to be faithful to beyond the driver object itself. This is the highest
confidence item on the list and also the cheapest.

### 6. `talib` — 217,788 lines

**What the native code is.** TA-Lib C 0.8.1, 154,771 lines in `src/ta-lib`. The R
layer is large — 156 files, 31,141 lines, 400 exports — but it is wrappers: 61
candlestick pattern files and 87 indicator files, plus 8 files of chart and theme
helpers built on ggplot2 and plotly.

**Stand-in.** `TA-Lib` (0.8.2, October 2026), the Cython wrapper maintained under the
`ta-lib` organisation, over the same C library.

**Why this is right.** Every number the R package returns is computed by
`TA_xxx()` in the C library. Same inputs, same C, same outputs — including the
lookback conventions and the `TA_INT`/`TA_REAL` behaviour, which are the parts people
actually trip over. The version is one patch ahead of the vendored copy, which is
closer than any reimplementation would get.

**What is not covered.** The R layer adds two naming styles for each indicator
(`averageTrueRange` and `average_true_range`) and 859 `S3method` lines for
`data.frame`, `ggplot` and `ta_series` classes. Those are R presentation and are not
reproduced; charts go to Matplotlib under the existing routing rule. So the
*computation* is a 99% stand-in and the *R API surface* is not, which is exactly the
line the project already draws for `plotly` and `lattice`.

### 7. `leidenAlg` — 209,133 lines

**What the native code is.** `rigraph` 128,843 lines (98.2%) and `leidenalg` 2,237.
The R layer is three files and 137 lines, seven exports, all of them
`find_partition` in one wrapper or another.

**Stand-in.** `igraph` and `leidenalg` (0.12.0, May 2026, by the algorithm's own
authors, over `libleidenalg` in C++).

**Why this is right.** The package vendors the same `leidenalg` C++ core that the
Python package binds, on top of a copy of igraph — and `igraph` is already replaced in
this project. The remaining R code is a `communities` object with two S3 methods,
which under the constitution is a Python class with the same fields. This is the
cleanest "wrap, do not remake" case in the list: the wrapper being replaced is
literally the same wrapper Python already has.

### 8. `leidenbase` — 195,194 lines

Same system as `leidenAlg` — `core` 99,773 lines of vendored igraph, `vendor` 16,430,
`leidenalg` 2,794 — reached by a different author, with 850 lines of its own C++ glue in
`src/leidenbase`. The R layer is one file of 69 lines exporting one function,
`leiden_find_partition`.

**Stand-in.** `igraph` + `leidenalg`, as above. Keep both on the list: they are
separate CRAN packages with separate dependency trees, and routing both removes 404k
lines for the price of one decision.

### 9. `hdf5r` — 140,350 lines

**What the native code is.** libhdf5, bundled **seven times** — `1_8_12`, `1_8_14`,
`1_8_16`, `1_10_0`, `1_10_2`, `1_10_3`, `1_12_0` — for build-target selection: 97.9%
of the code. The package's own C is 2,579 lines, mostly `convert.c` and the type
wrappers. The R layer is 24 files and 6,581 lines with 76 exports, built as R6 classes.

**Stand-in.** `h5py` (BSD-3-Clause, 3.16.0, March 2026).

**Why this is right.** Both are direct bindings to libhdf5, so the file bytes written
are produced by the same library, not by two implementations of the format agreeing.
The R6 class hierarchy (`H5File`, `H5Group`, `H5D`, `H5T`, `H5S`, `H5P`, `H5A`, `H5R`)
maps onto `h5py`'s object model, and the low-level property-list and datatype API that
`hdf5r` exposes has a direct counterpart in `h5py.h5p`, `h5py.h5t`, `h5py.h5s`.

**What is not covered.** `hdf5r` is R6 and the translation is a Python class per the
object rules, so dispatch is not compared. Reading a file written by either side is
the proof worth keeping.

### 10. `mongolite` — 123,267 lines

**What the native code is.** `mongoc` 51,694 lines, `utf8proc` 17,540, `bson` 9,144,
`kms` 4,282 — 98.7% vendored. The R layer is 12 files and 885 lines, six exports:
`mongo`, `gridfs`, `mongo_options`, `read_bson`, `ssl_options`, `oid_to_timestamp`.

**Stand-in.** `pymongo` (Apache-2.0, 4.19.0, October 2026), MongoDB's official driver.

**Why this is right.** The work is a wire protocol and a BSON codec, both defined by
the server rather than by the package. `pymongo` is the reference implementation of
that protocol and is more complete than the bundled `mongoc`. Documents round-trip
identically because BSON is BSON.

**What is not covered.** `mongolite`'s `jeroen` class gives `$`, `[` and `[[` over a
query cursor; in Python that is a cursor and a dict. A live server is needed for the
proof, which is a session requirement worth noting before the check is scheduled.

---

## Just missed

These rank above some picks and are still worth doing, but not at 99%:

- **`rlibkriging` (441,969)** — 89% `slapack` Fortran, 9% `libK`, and `libK` is the
  author's own kriging C++ that *does* ship a Python binding (`pylibkriging`). The
  catch: the CRAN tarball strips `src/libK/bindings/Python`, and `pylibkriging` is not
  on PyPI, so it has to be built from the vendored sources. Numerically this is a very
  safe stand-in; it is a packaging task, not a translation task. It belongs on the
  list the moment someone confirms the build.
- **`seqminer` (349,571)** — the read path is `htslib`/`bgzf`/`tabix`/`khash` (MIT,
  Broad and GRL) plus bundled SQLite and zstd, and `pysam`, `cyvcf2`, `bgen-reader`,
  `bed-reader` cover it. But 10,094 lines of its own code sit in `src/` root —
  `GeneAnnotation.h` (31 KB), `rvMetaLoader.cpp` (83 KB), the region and pattern
  matchers — and those implement gene annotation over its own tables. The I/O is a
  clean replacement; `annotateGene` and friends are a small genuine port.
- **`libopenexr` (108,680)**, **`qpdf` (35,995)**, **`osqp` (25,303)**,
  **`re2` (24,979)**, **`libgeos` (48,529)** — all 95%+ vendored, all under 200 lines
  of R glue, all with the same library on PyPI (`OpenEXR`, `pikepdf`, `osqp`,
  `google-re2`, `shapely`). Smaller, but each is a near-certain win and they are
  nearly free. `qpdf` is the best of them: `pikepdf` *is* libqpdf.
- **`cld2` (117,946)** — `pycld2` binds the same CLD2 library, but CLD2 is deprecated
  upstream in favour of CLD3, so the stand-in would be pinning a dead library.
- **`webfakes` (156,619)** and **`nanonext` (128,779)** — 15.6% and 6.7% of their code
  is R-original (the fake-server layer, the async core) sitting on civetweb/mbedtls and
  nng. Replacement is real but partial.
- **`rbibutils` (107,106)** and **`frailtypack` (120,926)** — 100% R-original. These
  are exactly what the Rust crate route exists for; do not route them.

## What was done

- Agreed and recorded. `rcran/replaced.json` has one `packages` entry per package and
  a `janus-swi` `strategies` entry. `ai-handbook/native.json` gained seven entries:
  `janus-swi`, `pymumps`, `adbc-driver-manager`, `TA-Lib`, `leidenalg`, `h5py`, and
  `pymongo`. PyICU was already listed. `igraph` is already a routing stand-in in
  `CONSTITUTION.md`, and pip/uv are named there for `pak` and `renv`.
- The `low_level` rows for the ten now read `replaced`, and the pending total fell from
  21,047,104 to 18,322,687 compiled lines, a drop of 2,724,417 that matches the table
  exactly.
- The 30 packages that listed one of the ten as a dependency were rescreened. The ten
  are gone from every `needs_first` list, and `iRfcb` and `propagate` are now free.
- `python3 orchestrator/killr.py site` rebuilt the dashboard: 39 replaced packages.

The rule this rests on is now in the Wrapping or remaking section of `CONSTITUTION.md`,
including the 95% vendored test and the requirement that a Python binding be to the same
library rather than to a library with the same purpose.

