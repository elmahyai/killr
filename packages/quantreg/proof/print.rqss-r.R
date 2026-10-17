suppressPackageStartupMessages(library(quantreg))
n <- 60
i <- 1:n
x <- 2 * sin(i)
z <- cos(0.7 * i)
y <- sin(x) + 0.5 * z + 0.3 * sin(7 * i)
d <- data.frame(y = y, x = x, z = z)
f1 <- rqss(y ~ qss(x, lambda = 2) + z, tau = 0.5, data = d)
f2 <- rqss(y ~ qss(x, lambda = 2) + qss(z, lambda = 1, Dorder = 0), tau = 0.5, data = d)
s1 <- summary(f1)
s2 <- summary(f2)
one <- function() {
  print(f1)
  print(f2)
  invisible(NULL)
}
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
value <- c(s1$fidelity, s1$edf, f1$tau, s2$fidelity, s2$edf, f2$tau)
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
