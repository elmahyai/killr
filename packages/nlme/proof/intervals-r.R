.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Fixed inputs: Orthodont gls fits with no structure (apVar = NULL). The first
## fit has REML estimated sigma; the second fixes sigma = 2 with glsControl.
data(Orthodont, package = "nlme")

fit_free <- gls(distance ~ age + Sex, Orthodont)
fit_fixed <- gls(distance ~ age + Sex, Orthodont, control = glsControl(sigma = 2))

one <- function() {
  a <- intervals(fit_free, level = 0.95, which = "all")
  b <- intervals(fit_fixed, level = 0.95, which = "all")
  c(
    as.numeric(a$coef), as.numeric(a$sigma),
    as.numeric(b$coef), as.numeric(b$sigma)
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
