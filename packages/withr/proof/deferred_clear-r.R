# Proof: R side of withr::deferred_clear (withr 3.0.3).
# Python name: withr.deferred.deferred_clear
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
  bucket <- character()
  f <- function() {
    defer(bucket <<- c(bucket, "a"))
    deferred_clear()
    defer(bucket <<- c(bucket, "b"))
  }
  f()
  list(bucket)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  one()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
}
emit(value, median(elapsed))
