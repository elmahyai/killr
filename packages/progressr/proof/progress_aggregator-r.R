.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
options(progressr.enable = TRUE)

one <- function() {
  amounts <- numeric()
  handler <- make_progression_handler("rec", reporter = list(
    update = function(config, state, progression, ...) {
      child <- progression$child
      if (!is.null(child)) amounts <<- c(amounts, child$amount)
    }
  ), enable = TRUE, target = "file", interval = 0)
  value <- with_progress({
    progress <- progressor(steps = 2, initiate = TRUE)
    relay <- progress_aggregator(progress)
    relay({
      p <- progressor(steps = 2)
      p(amount = 1)
      p(amount = 1)
      2
    })
  }, handlers = handler, enable = TRUE, interval = 0,
     delay_terminal = FALSE, delay_stdout = FALSE, delay_conditions = character())
  list(value = as.numeric(value), child_amounts = as.numeric(amounts))
}

ans <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%.17g,"child_amounts":[%s],"median_ms":%.17g}\n',
  ans$value,
  paste(sprintf("%.17g", ans$child_amounts), collapse = ","),
  median(elapsed) * 1000
))
