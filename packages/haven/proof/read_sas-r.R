
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(haven))
suppressPackageStartupMessages(library(jsonlite))
json_val <- function(x) {
  if (is.null(x)) return("null")
  toJSON(x, auto_unbox = TRUE, null = "null", digits = 17)
}

one <- function() {
  d <- read_sas("/home/ahmed/R/library/haven/examples/iris.sas7bdat", skip = 1)
  c(names(d)[1], as.character(nrow(d)), sprintf("%.1f", d[[1]][1]))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
