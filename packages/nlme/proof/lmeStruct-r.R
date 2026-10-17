.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(Pixel)
  rs1 <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  ls1 <- lmeStruct(rs1)
  ls2 <- lmeStruct(rs1, corStruct = corAR1(0.5))
  c(
    as.numeric(attr(ls1, "settings")),
    length(ls1),
    as.numeric(inherits(ls1, "lmeStruct")),
    as.numeric(inherits(ls1, "modelStruct")),
    as.numeric(names(ls1) == "reStruct"),
    length(ls2),
    as.numeric(c("reStruct", "corStruct") %in% names(ls2)),
    as.numeric(is.null(ls2$varStruct)),
    as.numeric(isInitialized(ls2$reStruct)),
    as.numeric(attr(ls2, "settings")),
    length(ls2$reStruct),
    as.numeric(inherits(ls2$corStruct, "corAR1"))
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
