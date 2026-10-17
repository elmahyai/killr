.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(minpack.lm))
stopifnot(packageVersion("minpack.lm") == "1.2.4")

pack <- function(ctrl) {
  diag_is_list <- is.list(ctrl$diag)
  if (is.null(ctrl$diag)) {
    diag_vals <- numeric(0)
    diag_len <- 0
  } else if (diag_is_list) {
    diag_vals <- as.numeric(unlist(ctrl$diag, use.names = FALSE))
    if (is.null(diag_vals)) diag_vals <- numeric(0)
    diag_len <- length(ctrl$diag)
  } else {
    diag_vals <- as.numeric(ctrl$diag)
    diag_len <- length(diag_vals)
  }
  maxfev_vals <- as.numeric(ctrl$maxfev)
  if (is.null(maxfev_vals)) maxfev_vals <- numeric(0)
  c(
    as.numeric(ctrl$ftol),
    as.numeric(ctrl$ptol),
    as.numeric(ctrl$gtol),
    as.numeric(ctrl$epsfcn),
    as.numeric(ctrl$factor),
    as.numeric(ctrl$maxiter),
    as.numeric(ctrl$nprint),
    as.numeric(diag_is_list),
    diag_len,
    diag_vals,
    as.numeric(is.integer(ctrl$maxfev)),
    length(maxfev_vals),
    maxfev_vals
  )
}

one <- function() {
  defaults <- nls.lm.control()
  example <- nls.lm.control(maxiter = 4)
  positional <- nls.lm.control(1e-4, 1e-5)
  numeric_diag <- nls.lm.control(
    ftol = 1e-6, ptol = 1e-7, gtol = 1e-5,
    diag = c(1.5, 2.5, 3.5), epsfcn = 1e-8, factor = 10,
    maxfev = 200, maxiter = 4, nprint = 1
  )
  integer_maxfev <- nls.lm.control(
    diag = list(2, 4), maxfev = 200L, maxiter = 4L, nprint = 1L
  )
  c(
    pack(defaults),
    pack(example),
    pack(positional),
    pack(numeric_diag),
    pack(integer_maxfev)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
