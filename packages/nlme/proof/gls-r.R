.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Fixed input: Orthodont with distance ~ age + Sex, no correlation and no
## weights (the default gls path, which needs no optimizer).
data(Orthodont, package = "nlme")

one <- function() gls(distance ~ age + Sex, Orthodont)

fm <- one()
value <- c(
  as.numeric(coef(fm)),
  as.numeric(fm$varBeta),
  fm$sigma,
  fm$logLik
)
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
