.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/deSolve/proof"
deso <- system.file("libs/deSolve.so", package = "deSolve")
so <- file.path(proof_dir, "lagvalue_dump.so")
if (!file.exists(so) || file.info(so)$mtime < file.info(file.path(proof_dir, "lagvalue_dump.c"))$mtime) {
  owd <- setwd(proof_dir)
  on.exit(setwd(owd), add = TRUE)
  system("R CMD SHLIB lagvalue_dump.c", ignore.stdout = TRUE)
  system(sprintf(
    "gcc -std=gnu23 -shared -o lagvalue_dump.so lagvalue_dump.o '%s' -L/usr/lib/R/lib -lR",
    deso
  ))
}
dyn.load(so)

derivs <- function(t, y, parms) {
  if (t < 1)
    lag1 <- cos(t - 1)
  else
    lag1 <- lagvalue(t - 1)[1]
  if (t < 2)
    lag2 <- sin(t - 2)
  else
    lag2 <- lagvalue(t - 2, 2)
  dlag <- if (t < 0.5) 0 else lagderiv(t - 0.5, 1)
  list(c(lag1 * lag2 + 0.01 * dlag, -y[1] * lag2))
}

yinit <- c(y1 = 0, y2 = 0)
times <- seq(0, 20, by = 0.01)

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

one <- function() {
  yout <- dede(y = yinit, times = times, func = derivs, parms = NULL, atol = 1e-9)
  invisible(yout)
  tq <- c(0.5, 1, 1.5, 2.5, 5, 10, 15, 19.5)
  out <- c(
    unlist(lapply(tq, lagderiv)),
    unlist(lapply(tq, function(tt) lagderiv(tt, 2))),
    as.numeric(lagderiv(7.25)),
    as.numeric(lagderiv(7.25, c(1, 2)))
  )
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

yout <- dede(y = yinit, times = times, func = derivs, parms = NULL, atol = 1e-9)
hist <- .Call("dump_lag_history")
snap <- list(
  histtime = as.numeric(hist$histtime),
  histvar = as.numeric(hist$histvar),
  histdvar = as.numeric(hist$histdvar),
  n_eq = hist$n_eq,
  histsize = hist$histsize,
  indexhist = hist$indexhist,
  starthist = hist$starthist,
  endreached = hist$endreached,
  offset = hist$offset,
  interpolMethod = hist$interpolMethod
)
writeLines(
  sprintf('{"value":%s,"median_ms":%.17g}', json_num(value), median(elapsed) * 1000),
  file.path(proof_dir, "lagderiv-r-out.json")
)
json_snap <- function(obj) {
  paste0(
    "{",
    paste(
      c(
        paste0('"histtime":', json_num(obj$histtime)),
        paste0('"histvar":', json_num(obj$histvar)),
        paste0('"histdvar":', json_num(obj$histdvar)),
        paste0('"n_eq":', obj$n_eq),
        paste0('"histsize":', obj$histsize),
        paste0('"indexhist":', obj$indexhist),
        paste0('"starthist":', obj$starthist),
        paste0('"endreached":', obj$endreached),
        paste0('"offset":', obj$offset),
        paste0('"interpolMethod":', obj$interpolMethod)
      ),
      collapse = ","
    ),
    "}"
  )
}
writeLines(json_snap(snap), file.path(proof_dir, "lagderiv-hist.json"))
