
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(haven))
suppressPackageStartupMessages(library(jsonlite))
json_val <- function(x) {
  if (is.null(x)) return("null")
  toJSON(x, auto_unbox = TRUE, null = "null", digits = 17)
}

one <- function() {
  tmp <- tempfile(fileext = ".sav")
  on.exit(unlink(tmp))
  x <- labelled_spss(c(1, 9, 11), c(Good = 1), na_values = 9, na_range = c(10, 12), label = "q")
  write_sav(tibble::tibble(q = x), tmp)
  d <- read_sav(tmp, user_na = TRUE)
  c(as.character(d$q), as.character(attr(d$q, "na_values")), as.character(attr(d$q, "na_range")), attr(d$q, "label"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
