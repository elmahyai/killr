.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
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
yout <- dede(y = yinit, times = times, func = derivs, parms = NULL, atol = 1e-9)
cat(sprintf("lagvalue(1.5): %s\n", paste(format(lagvalue(1.5), digits = 17), collapse = " ")))
cat(sprintf("lagvalue(1.5, 2): %.17g\n", lagvalue(1.5, 2)))
