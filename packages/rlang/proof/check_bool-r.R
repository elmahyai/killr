.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
if (as.character(packageVersion("rlang")) != "1.3.0") {
  stop("expected rlang 1.3.0")
}
one <- function() {
  n <- 1
  msg <- tryCatch(check_bool(n), error = function(e) conditionMessage(e))
  paste(
    is.null(check_bool(TRUE)),
    is.null(check_bool(FALSE)),
    is.null(check_bool(NA, allow_na = TRUE)),
    is.null(check_bool(NULL, allow_null = TRUE)),
    msg,
    sep = "|"
  )
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
