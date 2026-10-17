# Proof: R side of withr::local_ (withr 3.0.3).
# Python name: withr.factory.local_
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

state <- 0
setx <- function(new) {
  old <- state
  state <<- new
  old
}
resetx <- function(old) state <<- old
local_x <- local_(setx, resetx)

one <- function() {
  state <<- 0
  f <- function() {
    old <- local_x(5)
    c(old, state)
  }
  inside <- f()
  list(inside, state)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  one()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
}
emit(value, median(elapsed))
