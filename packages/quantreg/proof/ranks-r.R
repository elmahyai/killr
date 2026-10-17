suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[, 1:3]
y <- d[, 4]
df <- data.frame(y = y, x1 = X[, 2], x2 = X[, 3])
# The process object: rq(tau = -1) runs R's rqbr.f, which the Rust crate quantreg_br ports.
fit <- rq(y ~ x1 + x2, tau = -1, data = df)
one <- function() {
  a <- ranks(fit)
  b <- ranks(fit, trim = c(0.1, 0.9))
  c1 <- ranks(fit, score = "normal")
  c2 <- ranks(fit, score = "sign")
  c3 <- ranks(fit, score = "tau", tau = 0.25)
  c4 <- ranks(fit, score = "normalscale")
  c5 <- ranks(fit, score = "halfnormalscale")
  c6 <- ranks(fit, score = "lehmann")
  c7 <- ranks(fit, score = "interquartile")
  c(a$ranks, a$A2, b$ranks, b$A2, c1$ranks, c1$A2, c2$ranks, c2$A2,
    c3$ranks, c3$A2, c4$ranks, c4$A2, c5$ranks, c5$A2, c6$ranks, c6$A2,
    c7$ranks, c7$A2)
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
