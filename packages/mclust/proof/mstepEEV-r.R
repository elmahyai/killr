library(mclust)
i <- 1:24
x <- cbind(i / 10 + i %% 5, (i * i %% 7) / 3 - i / 20, (i * 3 %% 11) / 2 + i / 50)
raw <- cbind(1 + ((i + 2 * 1) %% 3), 1 + ((i + 2 * 2) %% 3))
z <- raw / rowSums(raw)
flat <- function(r) {
  v <- r$parameters$variance
  c(r$parameters$pro, r$parameters$mean, v$sigma, v$scale, v$shape, v$orientation)
}
one <- function() flat(mstepEEV(x, z)); value <- one(); times <- numeric(20)
for (j in seq_len(20)) { t0 <- Sys.time(); one(); times[j] <- as.numeric(difftime(Sys.time(), t0, units="secs")) * 1000 }
cat(paste(sprintf("%.17g", value), collapse="\n"), "\n", sep=""); cat(sprintf("%.17g\n", median(times)))
