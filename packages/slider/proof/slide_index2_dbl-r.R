
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
suppressPackageStartupMessages(library(jsonlite))
x <- c(1, 5, 3, 2, 6, 10)
y <- c(2, 4, 1, 3, 5, 7)
i <- c(0, 1, 3, 4, 6, 8)
ch <- c("a", "b", "c", "d", "e", "f")
lg <- c(TRUE, FALSE, TRUE, TRUE, FALSE, TRUE)
json_val <- function(value) {
  if (is.character(value)) {
    toJSON(value, auto_unbox = FALSE)
  } else {
    toJSON(as.numeric(value), auto_unbox = FALSE, digits = 17, na = "null")
  }
}

one <- function() {
  as.numeric(slide_index2_dbl(x, y, i, function(a, b) sum(a) - sum(b), .before = 2))
}
value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
