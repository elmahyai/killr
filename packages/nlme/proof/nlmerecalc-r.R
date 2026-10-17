.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

sym_symm <- get("symm_recalc", envir = asNamespace("nlme"))
sym_nat <- get("nat_recalc", envir = asNamespace("nlme"))
sym_ar1 <- get("AR1_recalc", envir = asNamespace("nlme"))
sym_comp <- get("compSymm_recalc", envir = asNamespace("nlme"))

xy <- c(0.5, -1.2, 0.3, 2.0, -0.7, 1.1, 0.0, 0.4,
        1.5, 0.2, -0.4, 0.8, 3.0, -1.0, 0.6, -0.3)
pdims <- c(8L, 3L, 4L, 26L, 4L, 1L, 3L, 0L, 4L, 5L)
time <- c(0L, 2L, 1L, 3L, 0L, 1L, 0L, 2L)
pars_symm <- c(-0.8, 0.3, 1.1, -0.4, 0.6, -1.5)
pars_nat <- c(0.4, -0.2, 0.1, 0.3, -0.5, 0.2)

one_symm <- function() {
  val <- .C(
    sym_symm,
    Xy = as.double(xy),
    as.integer(pdims),
    as.integer(2),
    as.double(pars_symm),
    as.integer(time),
    as.integer(4),
    logLik = 0.0,
    PACKAGE = "nlme"
  )
  c(val$Xy, val$logLik)
}

one_nat <- function() {
  val <- .C(
    sym_nat,
    Xy = as.double(xy),
    as.integer(pdims),
    as.integer(2),
    as.double(pars_nat),
    as.integer(time),
    as.integer(4),
    logLik = 0.0,
    PACKAGE = "nlme"
  )
  c(val$Xy, val$logLik)
}

one_ar1 <- function() {
  val <- .C(
    sym_ar1,
    Xy = as.double(xy),
    as.integer(pdims),
    as.integer(2),
    par = 1.2,
    logLik = 0.0,
    PACKAGE = "nlme"
  )
  c(val$Xy, val$par, val$logLik)
}

one_comp <- function() {
  val <- .C(
    sym_comp,
    Xy = as.double(xy),
    as.integer(pdims),
    as.integer(2),
    par = 0.55,
    as.double(-1 / 3),
    logLik = 0.0,
    PACKAGE = "nlme"
  )
  c(val$Xy, val$par, val$logLik)
}

report <- function(kernel, one) {
  value <- one()
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one()
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  cat(sprintf(
    "{\"kernel\":\"%s\",\"value\":[%s],\"median_ms\":%.17g}\n",
    kernel,
    paste(sprintf("%.17g", value), collapse = ","),
    median(elapsed) * 1000
  ))
}

report("symm_recalc", one_symm)
report("nat_recalc", one_nat)
report("ar1_recalc", one_ar1)
report("comp_symm_recalc", one_comp)
