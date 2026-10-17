.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

one <- function() {
  cs <- corAR1(0.2, form = ~ 1 | Mare)
  a <- glsStruct(corStruct = cs)
  b <- glsStruct()
  d <- glsStruct(corStruct = cs, varStruct = varExp(0.2, form = ~ age))
  c(
    length(a),
    length(b),
    length(d),
    as.numeric(inherits(a, "glsStruct")),
    as.numeric(inherits(a, "modelStruct")),
    as.numeric(identical(names(a), "corStruct")),
    as.numeric(identical(names(d), c("corStruct", "varStruct"))),
    as.numeric(inherits(d$varStruct, "varExp")),
    coef(a$corStruct),
    coef(a$corStruct, unconstrained = FALSE)
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
