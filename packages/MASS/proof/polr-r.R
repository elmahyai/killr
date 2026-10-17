.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
options(contrasts = c("contr.treatment", "contr.poly"))

one <- function() {
  data(housing, package = "MASS")
  fit <- polr(Sat ~ Infl + Type + Cont, weights = Freq, data = housing)
  c(coef(fit), fit$zeta, fit$deviance)
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
