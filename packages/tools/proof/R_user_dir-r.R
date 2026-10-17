suppressPackageStartupMessages(library(tools))

one <- function() {
  paste0(R_user_dir("tools", "data"), "|", R_user_dir("tools", "config"), "|", R_user_dir("tools", "cache"), "\n")
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
