suppressPackageStartupMessages(library(plyr))
stopifnot(identical(as.character(packageVersion("plyr")), "1.8.9"))

n <- 200000L
a <- (seq_len(n) * 17L) %% 23L
b <- (seq_len(n) * 13L) %% 97 / 10
c <- (seq_len(n) %% 11L) + (seq_len(n) %% 5L) / 2
a[seq(10L, n, 1000L)] <- NA
b[seq(20L, n, 1500L)] <- NA
b[seq(30L, n, 2500L)] <- NaN
c[seq(40L, n, 4000L)] <- Inf
c[seq(50L, n, 4000L)] <- -Inf
zeros <- which(b == 0)
b[zeros] <- -0
df <- data.frame(a = a, b = b, c = c)

one <- function() arrange(df, a, b, c)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

show_a <- function(v) ifelse(is.na(v), "NA", sprintf("%d", v))
show_d <- function(v) {
  ifelse(
    is.nan(v),
    "NaN",
    ifelse(is.na(v), "NA", ifelse(is.infinite(v), ifelse(v > 0, "Inf", "-Inf"), sprintf("%a", v)))
  )
}
cat("A ", paste(show_a(value$a), collapse = " "), "\n", sep = "")
cat("B ", paste(show_d(value$b), collapse = " "), "\n", sep = "")
cat("C ", paste(show_d(value$c), collapse = " "), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
