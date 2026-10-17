.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

derivs <- function(t, y, parms) {
  if (t < 1)
    lag1 <- cos(t - 1)
  else
    lag1 <- lagvalue(t - 1)[1]
  if (t < 2)
    lag2 <- sin(t - 2)
  else
    lag2 <- lagvalue(t - 2, 2)
  list(c(lag1 * lag2, -y[1] * lag2))
}

yinit <- c(y1 = 0, y2 = 0)
times <- seq(0, 20, by = 0.01)

json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}

one <- function() {
  yout <- dede(y = yinit, times = times, func = derivs, parms = NULL, atol = 1e-9)
  as.vector(yout)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
