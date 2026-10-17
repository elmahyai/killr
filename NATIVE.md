# Native

Read this with `CONSTITUTION.md` when a function uses the R session, a project root, or the path of the running script. A surprise goes in `experience/`, or in `packages/<Name>/experience/` when the package is `large` or `large-low`.

## A project root is a directory with a marker

The root is the directory that contains the marker. It is not a Python package, and it is not the process working directory unless the criterion says so. Walk parent directories from the start path, at most 100 steps, and stop at the filesystem root with the same error the R function raises.

Keep the marker names. `DESCRIPTION` whose contents match `^Package: ` is an R package root. A `.Rproj` file whose first line matches `^Version: ` is an RStudio project. The other markers used by rprojroot stay as they are: `.vscode/settings.json`, `remake.yml`, a `.drake` directory, `_targets.R`, the pkgdown yaml paths, `renv.lock` matching `"Packages":\s*\{`, `.projectile`, `_quarto.yml`, `.git` as a directory or as a file matching `^gitdir: `, and `.svn`.

`from_wd` is the current working directory. `is_testthat` is the directory name `testthat`, including the `tests/testthat` lookup. It does not load the testthat package.

## The running script is the file this process was started as

R recovers that path from `source()`'s `ofile`, from `R -f` or `--file`, from `Rscript --file`, or from `knitr::current_input`. Those are four lookups for one fact. Python returns the path of the file this process was started as, and `None` when there is no such file. Do not translate knitr or whereami. A soft-deprecation warning is printed by the package that owns the function. Do not translate lifecycle for that warning.

Check a script path by running a temp file under `Rscript` and under Python. An `Rscript -e` expression has no file. Do not compare it with a Python module that does.

## Paths

Use `/` separators. Follow symlinks the way `normalizePath(winslash = "/", mustWork = TRUE)` does. An absolute first component skips the root search. Mixing absolute and relative components is an error.

## A suggested package that is only a session hook is not translated

knitr, lifecycle, rlang, rmarkdown, testthat, withr, and covr are suggested by rprojroot. None of them is imported. Do not open a folder for them. When the hook is absent, return the same empty result R returns outside that session. `thisfile_knit` is `None` when nothing is being knitted.
