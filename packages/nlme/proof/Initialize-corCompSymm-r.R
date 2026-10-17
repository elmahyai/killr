.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

data <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c")
)

one <- function() {
  cc0 <- Initialize(corCompSymm(0.5, form = ~ 1 | Subject), data)
  cc1 <- Initialize(corCompSymm(-0.2, form = ~ 1 | Subject), data)
  c(
    as.vector(cc0),
    as.vector(coef(cc0, unconstrained = TRUE)),
    attr(cc0, "inf"),
    as.vector(attr(cc0, "factor")),
    as.vector(attr(cc0, "logDet")),
    coef(cc0, unconstrained = FALSE),
    as.vector(cc1),
    attr(cc1, "inf"),
    as.vector(attr(cc1, "factor")),
    as.vector(attr(cc1, "logDet")),
    coef(cc1, unconstrained = FALSE)
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
