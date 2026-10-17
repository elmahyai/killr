.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

pars <- c(K = 1, ka = 1e6, r = 1)
y <- c(A = 2, B = 3, D = 2 * 3 / pars["K"])
dy <- c(dA = 0, dB = 0, dD = 0)
prod <- matrix(
  ncol = 2,
  data = c(seq(0, 100, by = 10), seq(0.1, 0.5, len = 11))
)
outnames <- c("CONC", "Prod")
eval_times <- seq(0, 50, 2.5)

one <- function() {
  vals <- numeric(0)
  for (t in eval_times) {
    out <- DLLres(
      y = y,
      dy = dy,
      times = t,
      res = "chemres",
      dllname = "deSolve",
      initfunc = "initparms",
      initforc = "initforcs",
      parms = pars,
      forcings = prod,
      nout = 2,
      outnames = outnames
    )
    vals <- c(vals, as.numeric(out$delta), as.numeric(out$var))
  }
  vals
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
cat(sprintf(
  '{"value":%s,"median_ms":%.17g}\n',
  json_num(value), median(elapsed) * 1000
))
