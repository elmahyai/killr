suppressPackageStartupMessages(library(tools))

one <- function() {
  pid <- as.integer(system("sleep 30 >/dev/null 2>&1 & echo $!", intern=TRUE))
  ok <- pskill(pid)
  Sys.sleep(0.2)
  gone <- pskill(pid)
  paste0(ok, " ", gone, " ", pskill(-1), " ", pskill(10^9), "\n")
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
