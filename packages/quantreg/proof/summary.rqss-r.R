suppressPackageStartupMessages(library(quantreg))
n <- 60
i <- 1:n
x <- 2 * sin(i)
z <- cos(0.7 * i)
y <- sin(x) + 0.5 * z + 0.3 * sin(7 * i)
d <- data.frame(y = y, x = x, z = z)
f1 <- rqss(y ~ qss(x, lambda = 2) + z, tau = 0.5, data = d)
f2 <- rqss(y ~ qss(x, lambda = 2) + qss(z, lambda = 1, Dorder = 0), tau = 0.5, data = d)
g <- rqss(y ~ qss(x, lambda = 2) + qss(z, lambda = 1), tau = 0.5, data = d)
one <- function() {
  s1 <- summary(f1)
  s2 <- summary(f2)
  sg <- summary(g, cov = TRUE)
  c(as.vector(t(s1$coef)), s1$fidelity, s1$edf, s1$n,
    as.vector(t(s2$coef)), as.vector(t(s2$qsstab)), s2$fidelity, s2$edf, s2$n,
    as.vector(t(sg$coef)), as.vector(t(sg$qsstab)), sg$fidelity, sg$edf, sg$n,
    as.vector(t(as.matrix(sg$Vcov))), as.vector(t(as.matrix(sg$V))),
    unlist(lapply(sg$Vqss, function(v) as.vector(t(as.matrix(v))))))
}
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
value <- one()
# NaN and Inf are written as fixed sentinels so both sides can be compared cell by cell.
value <- ifelse(is.nan(value), -9e99, ifelse(is.infinite(value), ifelse(value > 0, 9e99, -9e98), value))
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
