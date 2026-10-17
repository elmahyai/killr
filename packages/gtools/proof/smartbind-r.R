.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

one <- function() {
  a <- data.frame(x = 1:2, y = c("a", "b"), check.names = FALSE)
  b <- data.frame(y = "c", z = 3, check.names = FALSE)
  out <- smartbind(a, b, fill = NA)
  apply(out, 1, function(row) paste(ifelse(is.na(row), "<NA>", trimws(row)), collapse = "|"))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  started <- Sys.time()
  invisible(one())
  elapsed[i] <- as.numeric(Sys.time() - started, units = "secs") * 1000
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n", format(median(elapsed), digits = 17), "\n", sep = "")
