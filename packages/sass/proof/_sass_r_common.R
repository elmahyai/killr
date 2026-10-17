# Shared helpers for the sass R proofs (sass 0.4.10 reference).
# Each <name>_r.R sources this file, then writes outputs/<name>_r.json.
# Canonical values are plain lists, so the Python proof can compare JSON.

suppressPackageStartupMessages(library(sass))
ns <- asNamespace("sass")

median_ms <- function(f, n = 20L) {
  invisible(f())                       # one untimed call
  t <- numeric(n)
  for (i in seq_len(n)) {
    t0 <- Sys.time()
    invisible(f())
    t[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  median(t)
}

# Run a case; an R error is recorded as the canonical error marker.
run_case <- function(f, canon = identity) {
  tryCatch(canon(f()), error = function(e) list(error = "error"))
}

canon_dep <- function(f) {
  e <- environment(f)
  x <- e$x
  dep_func <- e$dep_func
  kind <- if (identical(dep_func, ns$font_dep_face)) {
    "face"
  } else if (identical(dep_func, ns$font_dep_link)) {
    "link"
  } else if (identical(dep_func, ns$font_dep_google_local)) {
    "google_local"
  } else {
    "unknown"
  }
  href <- if (kind %in% c("link", "google_local")) x$href else NULL
  head <- NULL
  stylesheet <- NULL
  if (kind == "link") {
    head <- f()$head
  }
  if (kind == "face") {
    d <- f()
    stylesheet <- paste(readLines(file.path(d$src$file, d$stylesheet), warn = FALSE), collapse = "\n")
  }
  list(
    name = ns$font_dep_name(x),
    version = as.character(packageVersion("sass")),
    kind = kind,
    href = href,
    head = head,
    stylesheet = stylesheet
  )
}

canon_collection <- function(fc) {
  deps <- fc$html_deps
  if (is.null(deps)) deps <- list()
  if (is.function(deps)) deps <- list(deps)
  list(
    families = as.list(fc$families),
    default_flag = isTRUE(fc$default_flag),
    html_deps = lapply(deps, canon_dep)
  )
}

canon_layer <- function(l) {
  fa <- l$file_attachments
  list(
    functions = l$functions,
    defaults = l$defaults,
    mixins = l$mixins,
    rules = l$rules,
    declarations = l$declarations,
    html_deps = l$html_deps,
    file_attachments = if (is.null(fa)) NULL else as.list(fa)
  )
}

read_bytes_text <- function(path) {
  readChar(path, file.info(path)$size, useBytes = TRUE)
}

write_result <- function(path, fn_name, primary, r_ms, cases) {
  payload <- list(
    "function" = fn_name,
    primary_case = primary,
    r_ms = r_ms,
    sass_version = as.character(packageVersion("sass")),
    r_version = R.version.string,
    cases = cases
  )
  jsonlite::write_json(payload, path, auto_unbox = TRUE, null = "null", pretty = TRUE)
}

# Run every case (each returns a canonical value), time the primary call,
# then write the JSON result.
#   cases: named list of zero-argument functions returning canonical values.
#   timed: zero-argument function timed for r_ms (its inputs are built before).
run_proof <- function(fn_name, cases, timed, primary, out_path) {
  results <- list()
  for (nm in names(cases)) {
    results[nm] <- list(run_case(cases[[nm]]))
  }
  r_ms <- median_ms(timed)
  write_result(out_path, fn_name, primary, r_ms, results)
  message(sprintf("%s: R median %.6f ms over 20 calls", fn_name, r_ms))
  invisible(results)
}

script_here <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", grep("^--file=", args, value = TRUE)[1])
  dirname(normalizePath(f))
}
