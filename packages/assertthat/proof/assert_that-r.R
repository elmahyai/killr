suppressPackageStartupMessages(library(assertthat))

show <- function(res) {
  if (isTRUE(res)) "TRUE\n" else if (is.character(res)) paste0(res, "\n") else paste0(attr(res, "msg"), "\n")
}
one <- function() {
  ok <- assert_that(is.numeric(1))
  short <- tryCatch(assert_that(5 < 4), error = function(e) conditionMessage(e))
  long <- tryCatch(assert_that(isTRUE(10 + sqrt(25) + sum(1:10) + sqrt(25) + sum(11:20) + sqrt(25) + sum(21:30) + sqrt(25) + sum(31:40) + sqrt(25) + sum(41:50))), error = function(e) conditionMessage(e))
  paste0(if (isTRUE(ok)) "TRUE" else "FALSE", "\n", short, "\n", long, "\n")
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
