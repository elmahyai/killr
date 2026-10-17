.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(polynom))
one <- function() {
  paste(is.polylist(polylist(1)), is.polylist(polynomial(1)), sep=",")
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
