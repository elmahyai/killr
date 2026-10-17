.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
if (as.character(packageVersion("rlang")) != "1.3.0") {
  stop("expected rlang 1.3.0")
}
one <- function() {
  f <- quote(~foo)
  paste(
    paste(
      as.character(
        c(
          is_formula(~10),
          is_formula(10),
          is_formula(f),
          is_formula(f, scoped = TRUE),
          is_formula(~foo, lhs = FALSE),
          is_formula(quote(foo ~ bar), lhs = TRUE),
          is_formula(quote(foo ~ bar), lhs = FALSE)
        )
      ),
      collapse = ","
    ),
    sep = ""
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
