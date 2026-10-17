.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
if (as.character(packageVersion("rlang")) != "1.3.0") {
  stop("expected rlang 1.3.0")
}
one <- function() {
  ex1 <- parse_expr(c("1 + 2 *", "3"))
  ex2 <- parse_expr("foo(bar)")
  v1 <- eval_bare(ex1, env())
  err <- tryCatch(
    parse_expr("1; 2"),
    error = function(e) conditionMessage(e)
  )
  paste(v1, is_call(ex2, "foo"), err, sep = "|")
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
