# Constitution

This is the law for translating the CRAN catalog in this repository. The strategies are `small`, `medium`, `large`, `huge`, `small-low`, `medium-low`, `large-low`, and `hard-function`, under `strategies/`. A package is `small` at 20 functions still to translate, `medium` from 21 to 80, and `large` above that. A package with more than 200 exports is `huge`. `large` and `huge` assign a task force: functions in that package that are relevant to each other, finished together. That is not one function and not the rest of the package. `*-low` means the tarball has Fortran or C that computes. A function counts when it is not translated and `not_done` does not begin with `Left`. A session may run several packages. How many may be open is `strategies/orchestrator.md`. Each package follows the strategy stored on it, or the strategy the user names. The registry rules in `.cursor/rules/package-config.mdc` still apply.

## What is translated

The catalog already on disk under `cran/contrib`. The version comes from `cran/catalog.json` when that file exists, otherwise from the tarball name. Record the DESCRIPTION `Version`, dash included, as `cran_version`, and install that same version for the R comparison. Do not read GitHub, including `github.com/cran`, for the source or the help.

## Order

Before opening a package, finish every package in its DESCRIPTION `Depends` and `Imports` that is still untranslated and is not listed in `cran/replaced.json`. `Suggests` and `Enhances` do not block. `LinkingTo` is usually a C++ header package already routed away. Base packages are not opened as packages. When several packages are ready, the order is `cran/importance.json`, the last-month download ranking from the RStudio CRAN mirror. A dependency of a listed package is opened before that package. The old `_ranked` count is not the order. A `huge` package is checked for a stand-in before it is opened.

## A function is finished

The proof matches R within `1e-8`. One untimed call, then the median of 20. R uses `Sys.time()`. Python uses `time.perf_counter()`. `speedup` is the R time divided by the Python time. The two scripts live under `packages/<Name>/proof`. Save what the example prints or draws under `packages/<Name>/docs/output/`, and point `origin.output` and `translation.output` at those files. A `.txt` file is shown as text. An `.svg` file is shown as the figure. A function whose `not_done` begins with `Left` is not reserved.

## Close, not exact

`1e-8` is the only tolerance that makes a function finished. A proof that lands above it is not finished, and is never recorded as a match.

When a difference is real, small, and there is no better option, it may be kept as an **accepted difference**. That is a separate record, not a pass:

- `check.matches` means "matched at the tolerance recorded in `check.tolerance`". It is not a claim of `1e-8`.
- `check.tolerance` is the tolerance the difference was actually judged at.
- `check.max_abs_diff` is the measured difference.
- `check.approx_reason` says why the gap exists and why no better option is known. A reference-BLAS or floating-point cause is named in `experience/`, not repeated here.
- `not_done` still states what does not match, and for which cases.

The dashboard reads the numbers, not the flag: any recorded proof whose `max_abs_diff` is above `1e-8` is shown as `close`, whatever `matches` says. That keeps accepted differences apart from `proof checks`; they are labelled `close` in the comparison table and `+N close` in the tables and badges, and they never enter the passed count. An accepted difference is a note that the work is visible and unfinished, not a quiet pass. A function with an accepted difference is not `translated` unless the rest of its cases do match.

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

A package that compiles or links C++ into R, or a data bundle with no functions to call, is recorded in `cran/replaced.json` and is not translated. A resembling Python or Rust library is not a reason to call the package done.

A big library is a grammar, an application framework, a data-frame library, a geometry system, a graph library, an HTTP client, a sparse-matrix class system, or a document engine. Before one is reserved or replaced, name one mature Python alternative and ask. A small package, or one checkable function, does not wait. A Python or Rust library that is not already under `native` needs that same question. NumPy and Matplotlib are already agreed. After agreement, record it in `native.json` and rebuild the registry. A missing R package is reported and not created.

## Wrapping or remaking

Each R package is either a wrapper or original R code. The role decides the route:

- When R is only wrapping a C++ system, the C++ system is wrapped from Python or Rust. The R glue is not translated. The wrapper calls the C++ code through a Rust crate or a Python binding, and the library is listed in `native.json` before use. A whole C++ system is still asked about first, as Routing says. An example is `sass`, which wraps libsass.
- When the R code is original to R, the algorithm is remade in Rust or Python. This is the normal route for a statistical or algorithmic routine that the R package implements itself, including one whose kernel is written in C++ or Fortran. Such a kernel goes in `crates/<name>` under Kernels.

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
