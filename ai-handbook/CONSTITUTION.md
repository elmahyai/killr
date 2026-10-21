# Constitution

This is the law for translating the CRAN catalog in this repository. The strategies are `small`, `medium`, `large`, `huge`, `small-low`, `medium-low`, `large-low`, and `hard-function`, under `strategies/`. A package is `small` at 20 functions still to translate, `medium` from 21 to 80, and `large` above that. A package with more than 200 exports is `huge`. `large` and `huge` assign a task force: functions in that package that are relevant to each other, finished together. That is not one function and not the rest of the package. `*-low` means the tarball has Fortran or C that computes. A function counts when it is not translated and `not_done` does not begin with `Left`. A session may run several packages. How many may be open is `strategies/orchestrator.md`. Each package follows the strategy stored on it, or the strategy the user names. The registry rules in `.cursor/rules/package-config.mdc` still apply.

## What is translated

The catalog already on disk under `cran/contrib`. The version comes from `cran/catalog.json` when that file exists, otherwise from the tarball name. Record the DESCRIPTION `Version`, dash included, as `cran_version`, and install that same version for the R comparison. Do not read GitHub, including `github.com/cran`, for the source or the help.

## Order

Before opening a package, finish every package in its DESCRIPTION `Depends` and `Imports` that is still untranslated and is not listed in `cran/replaced.json`. `Suggests` and `Enhances` do not block. `LinkingTo` is usually a C++ header package already routed away. Base packages are not opened as packages. When several packages are ready, the order is `cran/importance.json`, the last-month download ranking from the RStudio CRAN mirror. A dependency of a listed package is opened before that package. The old `_ranked` count is not the order. A `huge` package is checked for a stand-in before it is opened.

## A function is finished

The proof matches R within `1e-8`. One untimed call, then the median of 20. R uses `Sys.time()`. Python uses `time.perf_counter()`. `speedup` is the R time divided by the Python time. The two scripts live under `packages/<Name>/proof`. Save what the example prints or draws under `packages/<Name>/docs/output/`, and point `origin.output` and `translation.output` at those files. A `.txt` file is shown as text. An `.svg` file is shown as the figure. A function whose `not_done` begins with `Left` is not reserved.

## Close is done

A proof that matches R within `1e-8` is **exact**. A proof whose best result is close, and where no better match was found, is **close**. Both are done. A package is finished when every function in it is exact, close, or `Left`.

Close is a decision, recorded, not a quiet pass:

- `check.matches` and `check.max_abs_diff` stay as measured. Do not raise `matches` to make a package look finished.
- `check.tolerance` is the tolerance the difference was judged at.
- `check.approx_reason` says why the gap exists and why no better option is known. A reference-BLAS or floating-point cause is named in `experience/`, not repeated here.
- The function record carries `"close": true` and a `close_note`, and its `not_done` still names what does not match and for which cases.
- Reopen it when a way to match R exactly is found. Close is a resting place, not a claim of equality.

The dashboard shows both. Close proofs are labelled `close` in the comparison table, `+N close` in the tables and badges, and a `close` function row. They are counted as done, so the package can finish; they are still reported apart from `proof checks`, so the exact count is never inflated.

Close is only for a difference no proof can remove. A function that is simply not written is not close. A case that was never run is not close.

## Routing

A package listed in `cran/replaced.json` is not translated. The reason names the stand-in. These choices are already made and are not checks at `1e-8`:

- Data frames are Polars, for dplyr, tidyr, tibble, tidyselect, reshape2, data.table, plyr, and pillar.
- Excel sheets are Polars `read_excel` through the Rust calamine reader, for readxl.
- Dashboards are Dash, for shiny, htmltools, and shinyjs.
- Charts are Matplotlib or one killplot function, including lattice. A chart of one to three Matplotlib lines calls Matplotlib. A missing chart function is added once in `killplot`. Do not translate `graphics`, `ggplot2`, `lattice`, or `grid` as charting systems.
- Interactive charts are the Python Plotly package, for plotly.
- HTTP calls are requests, for httr, httr2, and curl.
- XML and HTML documents use the system libxml2 through ctypes, for the rest of XML. xml2 is already finished that way. lxml is not the stand-in.
- Certificates, PKCS, and PEM are the Python cryptography package, for the rest of openssl. Hashes stay in hashlib. AES, RSA, Ed25519, and X25519 stay on libssl through the opensslport crate.
- Parallel loops are Rayon, for foreach, iterators, doParallel, and pbapply.
- Raster grids are rasterio, for terra and raster.
- Reports are Quarto, for rmarkdown and xtable.
- Database connections are SQLAlchemy, for DBI.
- The R session is Python, for rlang, generics, tools, utils, and rstudioapi.
- Vectors are NumPy, for vctrs.
- A Stan model stays a Stan program. Python sends it to the Stan program already on the machine through cmdstanpy, which runs CmdStan, for rstan. StanHeaders is the C++ headers and has no stand-in. cmdstanpy is not a check against rstan.
- A Prolog program stays a Prolog program. Python sends goals to the installed SWI-Prolog through janus-swi, which embeds the same libswipl that rswipl loads, for rswipl. The engine is not translated.
- Sparse direct solves are MUMPS through pymumps, for rmumps. The factorization is the same library, not a rearrangement of it.
- Arrow database access is adbc-driver-manager and adbc-driver-sqlite, for adbcsqlite. These are Apache's own bindings to the vendored project.
- Technical indicators are the TA-Lib Python package, for talib, over the same C library.
- HDF5 files are h5py, for hdf5r. h5py is a direct binding to libhdf5, so a file written either way comes from the same library.
- MongoDB documents are pymongo, for mongolite. The wire protocol and BSON are defined by the server.
- Community detection is python-igraph and leidenalg, for leidenAlg and leidenbase. leidenalg is by the algorithm's authors and wraps the same C++ core both packages vendor.
- A package that resolves or installs R packages is pip and uv, for pkgdepends, for pak, and for renv. R's packaging system does not exist on the Python side.
- ALTREP classes are not ported. R's internal character-vector representation has no Python counterpart to match, so ICU string semantics come from PyICU and the rest of charr is covered by the finished stringr port.

A package that compiles or links C++ into R, or a data bundle with no functions to call, is recorded in `cran/replaced.json` and is not translated. A resembling Python or Rust library is not a reason to call the package done.

A big library is a grammar, an application framework, a data-frame library, a geometry system, a graph library, an HTTP client, a sparse-matrix class system, or a document engine. Before one is reserved or replaced, name one mature Python alternative and ask. A small package, or one checkable function, does not wait. A Python or Rust library that is not already under `native` needs that same question. NumPy and Matplotlib are already agreed. After agreement, record it in `native.json` and rebuild the registry. A missing R package is reported and not created.

## Wrapping or remaking

Each R package is either a wrapper or original R code. The role decides the route:

- When R is only wrapping a C++ system, the C++ system is wrapped from Python or Rust. The R glue is not translated. The wrapper calls the C++ code through a Rust crate or a Python binding, and the library is listed in `native.json` before use. A whole C++ system is still asked about first, as Routing says. An example is `sass`, which wraps libsass.
- When the R code is original to R, the algorithm is remade in Rust or Python. This is the normal route for a statistical or algorithmic routine that the R package implements itself, including one whose kernel is written in C++ or Fortran. Such a kernel goes in `crates/<name>` under Kernels.

Which of the two applies is decided from the tarball, not from the package description. Read `src/` and ask how many lines sit outside the package's own directory:

- A package that is mostly vendored is a wrapper. When 95% or more of its compiled lines are an upstream library copied into `src/`, the package is not opened as a port. Its R layer is glue, and the library is wrapped from Python if a binding to that same library exists. Do not rewrite the library in Rust to make the wrapper unnecessary: a rewrite is a different program, so its numbers are only nearby, while a binding to the same library returns the same numbers. `rswipl`, `adbcsqlite`, `rmumps`, `hdf5r`, and `mongolite` are this shape.
- Fewer vendored lines means the algorithm is R's own, and it is remade. A package whose compiled code lives in its own `src/` root rather than in a vendored subdirectory is this shape; `frailtypack` and `rbibutils` are entirely their own code. The vendored fraction is a hint, not the decision: read what the top-level `src/` files compute before choosing.
- A vendored fork is still a wrapper even when the R package's own layer is large. `talib` is 31,141 lines of R over a vendored TA-Lib; the R is wrappers and chart themes, and every number comes from the C. Size of the R layer does not make the library R's.
- A Python binding has to be to the same library, not to a library with the same purpose. `pymumps` is MUMPS and `h5py` is libhdf5, so those stand in. A different sparse solver is not a stand-in for MUMPS even when it solves the same equation, because the ordering and the pivoting differ.
- Lines that implement R itself are excluded before the fraction is taken. C that only serves the evaluator, environments, or vector types is not a kernel under Kernels, so it is not code to remake whether or not it is vendored. `charr` is 82% vendored ICU and 18% R's ALTREP character representation: ICU is replaced by PyICU, and the ALTREP part is dropped rather than ported.

## Objects

Do not translate S3, S4, R6, or S7 into the same syntax. `new_class`, `new_generic`, properties, and validators are the R system. Python and Rust do not grow a copy of it. When another package uses one of those objects, the translation uses a Python class or a Rust struct that holds the same fields. The method body is an ordinary function. The caller uses Python or Rust call syntax. The proof compares the values, not the dispatch. `methods`, `R6`, and `S7` are the packages that carry an object system. They are not opened as ports of that system. An S3 generic with no method is an ordinary function.

## Kernels

Fortran, and C that computes, goes in `crates/<name>`. C that only implements R's evaluator, environments, or vector types is not a kernel and is not rewritten. Do not call R, `Rscript`, or `R --slave` to implement a function. The R proof may use `R --slave`. A listed crate is loaded, not ported again. Do not edit the workspace `Cargo.toml` from a sub-agent.

## Cost

The model is the first match in `strategies/orchestrator.md`. Cursor Settings → Models must include that slug; a disabled model is not available to Task. Easier Python batches use `gpt-5.6-luna-medium`. Skilled batches—an experience filename already matches, or the work is a crate or hard-function retry—use `claude-haiku-5-5-thinking-high` on Task, not the plain `claude-haiku-5-5` slug. Translation sub-agents pass the orchestrator slug on Task `model`; do not use `inherit` for those launches. The orchestrator lists at most three experience filenames in the launch prompt; the sub-agent opens only those files, as the Experience section says. Do not paste a whole experience file into a prompt. Do not rebuild the full dashboard. After a check is recorded, run `python3 dashboard/build.py --home`.

## Experience

The filename is the experience. It is at most four words and says what the lessons are about. Shared facts live in `experience/`. A fact true only inside a `large` or `large-low` package lives in `packages/<Name>/experience/`. List those filenames. Open at most three that match this function, in this turn, and do not open the rest. A second prompt is not sent for those bodies. A new fact goes in the file whose name already describes it. If no filename matches, add a new file with a name of at most four words that says what the fact is. One new or edited lesson per agent. Do not put a fact in a file whose name does not match it.

## Session and paths

Read `NATIVE.md` when a function uses the R session, a project root, or the path of the running script.

## When to stop

When the named hour budget ends, leave the remaining functions unassigned and the package in progress. Set `dependencies` only when the package is complete. `translated` names another registry package this one loads. `native` names a library in `native.json`. `rust` names a crate under `crates/`. A helper that lives only inside this package stays off the list. A non-empty `assigned` on any function means another agent owns that work. A sub-agent does not edit `translation.json`, the package `__init__.py`, `bench.py`, the dashboard, or the workspace `Cargo.toml`. The session that owns the package records the check.

## Waiting

`loads` names the other R packages a function calls. `blocked_by` names those that are still untranslated and not listed in `cran/replaced.json`. Base packages and a routed package are not a block. Empty `blocked_by` means the function is doable. A non-empty `blocked_by` means it is waiting, and `not_done` is `Waiting on <name>.` A sub-agent does not translate a waiting function and does not open the other package. It keeps going through the doable functions and returns the waiting names. The orchestrator writes those names on the function and sets the package `blocked_by` to the union. The next package it opens is one of those names, still under Order. When that package is finished or routed, the orchestrator removes its name from every `blocked_by`. A function whose list is then empty is doable and may be assigned. A new Python or Rust library that is not under `native` is not this list. That still stops and asks, as Routing says.
