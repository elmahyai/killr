.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}
dat <- data.frame(
  age = c(1, 2, 3, 4, 5, 6),
  Sex = factor(c("F", "F", "M", "M", "F", "M"))
)

one <- function() {
  g1 <- Initialize(varExp(0.2, form = ~ age | Sex), dat)
  s1 <- Initialize(varExp(0.3, form = ~ age), dat)
  u1 <- Initialize(varExp(form = ~ age), dat)
  c(
    as.vector(coef(g1, unconstrained = FALSE, allCoef = TRUE)),
    as.vector(varWeights(g1)), as.numeric(attr(g1, "logLik")),
    as.vector(coef(s1, unconstrained = TRUE)),
    as.vector(varWeights(s1)), as.numeric(attr(s1, "logLik")),
    as.vector(coef(u1, unconstrained = TRUE)),
    as.vector(varWeights(u1)), as.numeric(attr(u1, "logLik"))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
