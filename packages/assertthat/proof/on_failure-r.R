suppressPackageStartupMessages(library(assertthat))

show <- function(res) {
  if (isTRUE(res)) "TRUE\n" else if (is.character(res)) paste0(res, "\n") else paste0(attr(res, "msg"), "\n")
}
one <- function() {
  is_red <- function(x) x == "red"
  on_failure(is_red) <- function(call, env) paste0(deparse(call$x), " is not red")
  show(see_if(is_red("blue")))
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
