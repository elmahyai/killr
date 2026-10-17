.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(progressr))

one <- function() {
  seen <- 0L
  handler <- make_progression_handler("rec", reporter = list(
    initiate = function(config, state, progression, ...) {
      seen <<- seen + 1L
    },
    update = function(config, state, progression, ...) {
      seen <<- seen + 1L
    }
  ), enable = TRUE, target = "file", interval = 0)
  total <- withCallingHandlers({
    without_progress({
      p <- progressor(along = 1:5)
      s <- 0
      for (x in 1:5) {
        s <- s + x
        p(message = as.character(x))
      }
      s
    })
  }, progression = handler)
  list(sum = total, seen = seen)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"sum":%.17g,"seen":%.17g,"median_ms":%.17g}\n',
  value$sum, value$seen, median(elapsed) * 1000
))
