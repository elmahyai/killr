.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

data <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c")
)

one <- function() {
  cs0 <- Initialize(corSymm(form = ~ 1 | Subject), data)
  cs1 <- Initialize(
    corSymm(c(0.3, 0.1, 0.2, 0.05, 0.1, 0.25), form = ~ 1 | Subject),
    data
  )
  c(
    as.vector(cs0),
    as.vector(coef(cs0, unconstrained = TRUE)),
    as.vector(attr(cs0, "factor")),
    as.vector(attr(cs0, "logDet")),
    attr(cs0, "maxCov"),
    as.vector(cs1),
    as.vector(coef(cs1, unconstrained = FALSE))
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
