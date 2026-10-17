.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(Pixel)
  rs <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  ns <- nlmeStruct(reStruct = rs, corStruct = corAR1(0.3, form = ~1 | Dog))
  ns2 <- nlmeStruct(reStruct = rs)
  c(
    length(ns), length(ns2), length(nlmeStruct(reStruct = NULL)), length(class(ns)),
    as.numeric(attr(ns, "settings")),
    as.numeric(coef(ns$corStruct, unconstrained = TRUE)),
    length(ns$reStruct),
    as.numeric(attr(ns2, "settings")),
    as.numeric(is.null(ns2$corStruct)),
    as.numeric(is.null(nlmeStruct(reStruct = NULL)$reStruct))
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
