suppressPackageStartupMessages(library(assertthat))

one <- function() {
  x <- 1:3
        bare <- has_name(x, "a")
        names(x) <- letters[1:3]
        c(bare, has_name(x, "b"), has_name(x, "something else"), has_name(x, NA), has_name(x, c("a", "b")), has_name(x, c("a", "b", "c")), has_name(x, c("a", "d")))
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
