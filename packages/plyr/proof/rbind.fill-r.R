suppressPackageStartupMessages(library(plyr))
stopifnot(identical(as.character(packageVersion("plyr")), "1.8.9"))

n <- 20000L
x <- (seq_len(n) * 3) / 7
y <- (seq_len(n) %% 11L) + 0.5
z <- seq_len(n) * 1.25
a <- data.frame(x = x, y = y)
b <- data.frame(y = (seq_len(n) %% 13L) / 3, z = z)

one <- function() rbind.fill(a, b)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

show <- function(v) ifelse(is.na(v), "NA", sprintf("%a", v))
cat("NAMES ", paste(names(value), collapse = " "), "\n", sep = "")
cat("X ", paste(show(value$x), collapse = " "), "\n", sep = "")
cat("Y ", paste(show(value$y), collapse = " "), "\n", sep = "")
cat("Z ", paste(show(value$z), collapse = " "), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
