# Proof: R side of withr::local_timezone (withr 3.0.3).
# Python name: withr.timezone.local_timezone
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
  fmt <- function() format(as.POSIXct(0, origin = "1970-01-01"), "%H:%M %Z")
  default <- fmt()
  f <- function() {
    local_timezone("Asia/Tokyo")
    fmt()
  }
  inside <- f()
  list(inside, as.numeric(identical(fmt(), default)))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  one()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
}
emit(value, median(elapsed))
