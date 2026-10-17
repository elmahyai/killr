suppressPackageStartupMessages(library(tools))

one <- function() {
  s1 <- Rcmd(c("config", "CC"))
  s2 <- Rcmd(c("config", "NOT_A_VAR"))
  paste0("S ", s1, " ", s2, "\n")
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
