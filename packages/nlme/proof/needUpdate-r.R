.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  data(Pixel)
  rs <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  c(
    as.numeric(needUpdate(corAR1(0.3, form = ~1 | Dog))),
    as.numeric(needUpdate(rs)),
    as.numeric(needUpdate(varIdent(form = ~1))),
    as.numeric(needUpdate(varComb(varIdent(form = ~1), varIdent(form = ~1)))),
    as.numeric(needUpdate(nlmeStruct(reStruct = structure(1, needUpdate = TRUE)))),
    as.numeric(needUpdate(nlmeStruct(reStruct = structure(1, needUpdate = FALSE),
                                     corStruct = corAR1(0.3)))),
    as.numeric(needUpdate(structure(2, needUpdate = TRUE))),
    as.numeric(needUpdate(structure(2, needUpdate = FALSE))),
    as.numeric(needUpdate(structure(2)))
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
