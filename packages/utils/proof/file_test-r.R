library(utils)

one <- function() {
  dir <- file.path(R.home(), "library", "stats")
  paste(
    as.integer(file_test("-d", dir)),
    as.integer(file_test("-nt", file.path(dir, "R"), file.path(dir, "demo"))),
    sep = ","
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
