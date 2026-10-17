.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
if (as.character(packageVersion("rlang")) != "1.3.0") {
  stop("expected rlang 1.3.0")
}

checker <- function(foo, f, ...) {
  f(foo, ...)
}

one <- function() {
  empty <- data.frame()
  ok <- is.null(check_data_frame(empty))
  msg1 <- tryCatch(checker(, check_data_frame), error = function(e) conditionMessage(e))
  msg2 <- tryCatch(checker(NULL, check_data_frame), error = function(e) conditionMessage(e))
  msg3 <- tryCatch(
    checker(list(data.frame(), data.frame()), check_data_frame, allow_null = TRUE),
    error = function(e) conditionMessage(e)
  )
  paste(ok, msg1, msg2, msg3, sep = "|")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
