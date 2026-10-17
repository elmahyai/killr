# Proof: R side of withr::with_tempdir (withr 3.0.3).
# Python name: withr.tempfiles.with_tempdir
# Observable result: the values the call returns and the state it leaves
# behind, flattened to numbers and strings. One untimed call, then the
# median of 20 timed calls (Sys.time()). Prints one JSON line.

suppressPackageStartupMessages(library(withr))

emit <- function(value, ms) {
  items <- character()
  for (piece in value) {
    for (item in piece) {
      if (is.character(item)) {
        items <- c(items, paste0('"', item, '"'))
      } else {
        items <- c(items, sprintf("%.17g", as.numeric(item)))
      }
    }
  }
  cat(sprintf('{"value": [%s], "median_ms": %.6f}\n',
              paste(items, collapse = ", "), ms))
}

one <- function() {
  before <- getwd()
  holder <- new.env()
  inside <- with_tempdir({
    holder$dir <- getwd()
    c(as.numeric(startsWith(basename(getwd()), "file")), as.numeric(dir.exists(getwd())))
  })
  list(inside, as.numeric(identical(getwd(), before)), as.numeric(dir.exists(holder$dir)))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  one()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
}
emit(value, median(elapsed))
