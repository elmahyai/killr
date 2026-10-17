.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  d <- data.frame(
    y = c(5, 3, 8, 2, 6, 4),
    x1 = c(0, 1, 1, 0, 1, 0),
    x2 = c(1, 0, 1, 0, 0, 1),
    x3 = c(0, 0, 1, 1, 1, 0)
  )
  m0 <- glm(y ~ x1 + x2 + x3, family = poisson(), data = d)
  s <- stepAIC(
    m0,
    scope = list(upper = ~x1 + x2 + x3, lower = ~x1),
    direction = "both",
    trace = FALSE
  )
  c(
    deviance(s),
    s$rank,
    as.vector(unlist(s$anova[, c("Df", "Deviance", "Resid. Df", "Resid. Dev", "AIC")]))
  )
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
