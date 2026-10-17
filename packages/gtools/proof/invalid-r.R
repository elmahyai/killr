.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

fmt <- function(v) if (isTRUE(v)) "TRUE" else "FALSE"

one <- function() {
  failed <- try(log("A"), silent = TRUE)
  paste(
    c(
      fmt(invalid(NULL)),
      fmt(invalid(42)),
      fmt(invalid(numeric(0))),
      fmt(invalid(NA)),
      fmt(invalid(failed))
    ),
    collapse = "|"
  )
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
