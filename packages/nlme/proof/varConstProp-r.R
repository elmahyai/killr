.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

enc <- function(vf) {
  c(
    unlist(vf),
    as.vector(attr(vf, "whichFix")),
    attr(vf[["const"]], "fixed"),
    attr(vf[["prop"]], "fixed"),
    sum(utf8ToInt(deparse(formula(vf))))
  )
}

one <- function() {
  a <- varConstProp(const = 1.2, prop = 0.2, form = ~age | Sex)
  b <- varConstProp(const = 2, prop = 0.5)
  cc <- varConstProp(const = 3, prop = 0.2, fixed = list(const = 2))
  c(enc(a), enc(b), enc(cc))
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
