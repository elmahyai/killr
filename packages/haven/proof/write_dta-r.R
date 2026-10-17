
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(haven))
suppressPackageStartupMessages(library(jsonlite))
json_val <- function(x) {
  if (is.null(x)) return("null")
  toJSON(x, auto_unbox = TRUE, null = "null", digits = 17)
}

one <- function() {
  tmp <- tempfile(fileext = ".dta")
  on.exit(unlink(tmp))
  x <- labelled(c(1, tagged_na("a")), c(ok = 1, ABC = tagged_na("a")), label = "lab")
  write_dta(tibble::tibble(x = x), tmp, label = "hello")
  d <- read_dta(tmp)
  c(attr(d, "label"), attr(d$x, "label"), na_tag(d$x)[2], as.character(d$x[1]))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
