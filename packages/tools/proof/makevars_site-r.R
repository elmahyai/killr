suppressPackageStartupMessages(library(tools))

one <- function() {
  f <- tempfile()
  writeLines("X=1", f)
  Sys.setenv(R_MAKEVARS_SITE=f)
  hit <- makevars_site()
  paste0(if (identical(hit, f)) "HIT" else hit, "\n")
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
