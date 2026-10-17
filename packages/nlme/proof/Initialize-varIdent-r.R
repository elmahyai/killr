.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

data <- data.frame(
  y = 1:9,
  grp = factor(c("A", "A", "B", "B", "C", "C", "A", "B", "C"))
)

one <- function() {
  vf1 <- Initialize(varIdent(value = c(B = 2, C = 3), form = ~ 1 | grp), data)
  vf2 <- Initialize(
    varIdent(value = c(B = 2), fixed = c(C = 3), form = ~ 1 | grp),
    data
  )
  vf3 <- Initialize(varIdent(form = ~ 1), data)
  c(
    as.vector(coef(vf1, unconstrained = TRUE)),
    as.vector(coef(vf1, unconstrained = FALSE, allCoef = TRUE)),
    as.vector(varWeights(vf1)),
    as.vector(attr(vf1, "logLik")),
    as.vector(coef(vf2, unconstrained = TRUE)),
    as.vector(coef(vf2, unconstrained = FALSE, allCoef = TRUE)),
    as.vector(varWeights(vf2)),
    as.vector(attr(vf2, "logLik")),
    as.vector(coef(vf3, unconstrained = TRUE)),
    as.vector(varWeights(vf3)),
    as.vector(attr(vf3, "logLik"))
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
