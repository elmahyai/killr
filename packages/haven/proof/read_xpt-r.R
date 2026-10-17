
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(haven))
suppressPackageStartupMessages(library(jsonlite))
json_val <- function(x) {
  if (is.null(x)) return("null")
  toJSON(x, auto_unbox = TRUE, null = "null", digits = 17)
}

one <- function() {
  tmp <- tempfile(fileext = ".xpt")
  on.exit(unlink(tmp))
  write_xpt(tibble::tibble(num = c(1, 2, 3.5), txt = c("a", "b", "c")), tmp, version = 8, name = "T")
  d <- read_xpt(tmp)
  c(sprintf("%.1f", d$num), d$txt)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
