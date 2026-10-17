.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  d <- data.frame(
    y = c(5, 3, 8, 2),
    x1 = c(0, 1, 1, 0),
    x2 = c(1, 0, 1, 0)
  )
  m0 <- glm(y ~ x1, family = poisson(), data = d)
  addterm(m0, ~ . + x2, test = "Chisq")
  m1 <- glm(y ~ x1 + x2, family = poisson(), data = d)
  a <- dropterm(m1, test = "Chisq")
  as.vector(t(as.matrix(a)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
