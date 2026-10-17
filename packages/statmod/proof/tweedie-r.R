suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  mus <- exp(seq(log(0.05), log(20), length.out = 25))
  y <- mus * c(rep(0, 5), rep(1.1, 20))
  wt <- rep(1, length(y))
  f0 <- tweedie()
  f15 <- tweedie(var.power = 1.5, link.power = 0)
  f2 <- tweedie(var.power = 2, link.power = -1)
  f3 <- tweedie(var.power = 3, link.power = 0)
  suppressMessages(fchr <- tweedie(var.power = "gamma", link.power = "log"))
  eta0 <- f0$linkfun(mus)
  eta15 <- f15$linkfun(mus)
  c(
    as.numeric(f0$linkinv(eta0)),
    as.numeric(f0$mu.eta(eta0)),
    as.numeric(f0$variance(mus)),
    as.numeric(f0$dev.resids(y, mus, wt)),
    as.integer(f0$validmu(mus)),
    as.integer(f0$valideta(eta0)),
    as.numeric(f15$linkinv(eta15)),
    as.numeric(f15$mu.eta(eta15)),
    as.numeric(f15$variance(mus)),
    as.numeric(f15$dev.resids(y, mus, wt)),
    as.integer(f15$validmu(mus)),
    as.numeric(f2$linkfun(mus[1:3])),
    as.numeric(f2$dev.resids(y, mus, wt)),
    as.numeric(f3$linkfun(mus[1:3])),
    as.numeric(fchr$variance(mus[1:5])),
    as.numeric(fchr$dev.resids(y, mus, wt))
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
