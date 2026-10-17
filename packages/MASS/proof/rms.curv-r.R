.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))

data(Puromycin)
mmcurve <- deriv3(
  ~Vm * conc / (K + conc),
  c("Vm", "K"),
  function(Vm, K, conc) NULL
)
Treated <- Puromycin[Puromycin$state == "treated", ]
Purfit1 <- nls(
  rate ~ mmcurve(Vm, K, conc),
  data = Treated,
  start = list(Vm = 200, K = 0.1)
)

one <- function() {
  x <- rms.curv(Purfit1)
  c(x$pe, x$ic, x$ct, x$ci, as.vector(x$C))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = "\n"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
