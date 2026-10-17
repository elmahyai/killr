.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(curl))
one <- function() {
  path <- tempfile(); writeBin(charToRaw("Zed"), path); got <- "missing"; h <- new_handle(url = paste0("file://", path)); pool <- new_pool(); multi_add(h, done = function(x) got <<- rawToChar(x$content), pool = pool); multi_run(pool = pool); got
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
