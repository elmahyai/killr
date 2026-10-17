suppressPackageStartupMessages(library(assertthat))

one <- function() {
  x <- 1:3
        bare <- has_attr(x, "names")
        names(x) <- letters[1:3]
        c(bare, has_attr(x, "names"), has_attr(x, "something else"), has_attr(has_attr, "fail"), has_attr(10, "a"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(as.integer(value), collapse = " "), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
