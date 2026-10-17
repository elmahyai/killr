# Shared helpers for the locfit R reference scripts.
# Run from the repository root, for example:
#   Rscript packages/locfit/proof/rbox_r.R
# The reference is locfit 1.5-9.12 installed at LOCFIT_RLIB (default /tmp/locfit-rlib).

suppressMessages({
  library(locfit, lib.loc = Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib"))
  library(jsonlite)
})

OUT <- "packages/locfit/docs/output"
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

# Fixed inputs. The fits are built with locfit() here, on the R side only;
# the Python proofs read the stored JSON and never call R.
fixed_fits <- function() {
  x <- seq(0, 1, length.out = 25)
  set.seed(2)
  y <- sin(2 * pi * x) + 0.1 * rnorm(25)
  list(
    tree = locfit(y ~ x, alpha = 0.5, deg = 2),
    dat = locfit(y ~ x, ev = dat(), alpha = 0.5),
    grid = locfit(y ~ x, alpha = 0.5, ev = lfgrid(7))
  )
}

# Plain copy of an R object for JSON: named vectors become objects,
# S3 classes are dropped, and lists keep their names.
to_plain <- function(x) {
  if (is.list(x)) {
    y <- lapply(x, to_plain)
    names(y) <- names(x)
    return(y)
  }
  if (is.numeric(x) && !is.matrix(x) && !is.null(names(x))) {
    return(as.list(x))
  }
  x
}

# A fit as a fixed input: the components the translated helpers read.
fit_fixture <- function(fit) {
  to_plain(fit[c("eva", "mi", "nvc", "cell", "dp", "vnames")])
}

write_fixture <- function(x, name) {
  path <- file.path(OUT, paste0("locfit_", name, "_fixture.json"))
  writeLines(toJSON(x, auto_unbox = TRUE, digits = 17, na = "null", null = "null"), path)
  invisible(path)
}

write_r_output <- function(x, name) {
  path <- file.path(OUT, paste0("locfit_", name, "_r.json"))
  writeLines(toJSON(x, auto_unbox = FALSE, digits = 17, na = "null", null = "null"), path)
  invisible(path)
}

# Median per-call time in ms. One untimed call, then 20 timed samples; each
# sample is a loop of 20 calls, so R's timer resolves fast functions.
time_r_ms <- function(fn) {
  fn()
  samples <- numeric(20)
  for (i in seq_len(20)) {
    start <- Sys.time()
    for (j in seq_len(20)) fn()
    samples[i] <- as.numeric(difftime(Sys.time(), start, units = "secs")) * 1000 / 20
  }
  median(samples)
}

write_r_timing <- function(name, ms) {
  path <- file.path(OUT, paste0("locfit_", name, "_r_timing.txt"))
  writeLines(sprintf("r_ms=%.17g", ms), path)
  invisible(path)
}
