.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data <- data.frame(
    y = 1:6,
    x = c(1.2, 2.5, 3.1, 4.0, 5.5, 6.3)
  )
  vf <- varPower(0.35, form = ~x)
  vf <- Initialize(vf, data)
  c(
    as.vector(coef(vf, unconstrained = TRUE)),
    as.vector(coef(vf, unconstrained = TRUE, allCoef = TRUE)),
    as.vector(varWeights(vf))
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
