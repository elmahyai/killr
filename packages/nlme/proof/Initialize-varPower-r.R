.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

data <- data.frame(
  y = 1:6,
  x = c(1.2, 2.5, 3.1, 4.0, 5.5, 6.3),
  grp = c("A", "A", "B", "B", "A", "B")
)

one <- function() {
  vf1 <- Initialize(varPower(0.35, form = ~ x), data)
  vf2 <- Initialize(varPower(value = c(A = 0.3, B = 0.6), form = ~ x | grp), data)
  c(
    as.vector(coef(vf1, unconstrained = TRUE)),
    as.vector(coef(vf1, unconstrained = TRUE, allCoef = TRUE)),
    as.vector(varWeights(vf1)),
    as.vector(attr(vf1, "logLik")),
    as.vector(coef(vf2, unconstrained = TRUE)),
    as.vector(coef(vf2, unconstrained = TRUE, allCoef = TRUE)),
    as.vector(varWeights(vf2)),
    as.vector(attr(vf2, "logLik"))
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
