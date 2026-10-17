suppressPackageStartupMessages(library(assertthat))

show <- function(res) {
  if (isTRUE(res)) "TRUE\n" else if (is.character(res)) paste0(res, "\n") else paste0(attr(res, "msg"), "\n")
}
one <- function() {
  is_odd <- function(x) {
    assert_that(is.numeric(x), length(x) == 1)
    x %% 2 == 1
  }
  before <- show(see_if(is_odd(2)))
  on_failure(is_odd) <- function(call, env) paste0(deparse(call$x), " is even")
  after <- show(see_if(is_odd(2)))
  paste0(before, after)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
