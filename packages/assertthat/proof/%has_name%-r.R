suppressPackageStartupMessages(library(assertthat))

show <- function(res) {
  if (isTRUE(res)) "TRUE\n" else if (is.character(res)) paste0(res, "\n") else paste0(attr(res, "msg"), "\n")
}
one <- function() {
  y <- list(a = 1, b = 2)
  paste0(show(see_if(y %has_name% "c")), show(see_if(y %has_name% c("a", "g", "f"))))
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
