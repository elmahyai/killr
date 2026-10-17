.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(vctrs))
one <- function() {
  paste(paste(list_unchop(list(1:2, 3:4)), collapse = ","), paste(list_unchop(list(1, 2:3), indices = list(c(1, 3, 5), c(2, 4))), collapse = ","), sep = "/")
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
