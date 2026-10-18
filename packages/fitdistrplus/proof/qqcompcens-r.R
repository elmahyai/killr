pkg <- "/home/ahmed/killr_projects/killr/rcran/contrib/fitdistrplus_1.2-6.tar.gz"
lib <- path.expand("~/R/x86_64-pc-linux-gnu-library/4.5")
if (!requireNamespace("fitdistrplus", quietly = TRUE, lib.loc = lib))
  stop("fitdistrplus is not installed")
library(fitdistrplus, lib.loc = lib)

left <- c(-Inf, 0, 1, 2, 4, 5)
right <- c(0, 1, 2, 4, 5, Inf)
fit <- list(
  estimate = c(mean = 2.2, sd = 1.4), method = "mle",
  censdata = data.frame(left = left, right = right),
  distname = "norm", fix.arg = NULL, weights = NULL
)
class(fit) <- "fitdistcens"

values <- function() {
  f <- fitdistrplus:::npmle(fit$censdata, method = "Turnbull.intervals")
  p0 <- c(0, cumsum(f$p)[-length(f$p)])
  p1 <- cumsum(f$p)
  data.frame(
    left = f$left, right = f$right, p = f$p,
    qleft = qnorm(p0, fit$estimate["mean"], fit$estimate["sd"]),
    qright = qnorm(p1, fit$estimate["mean"], fit$estimate["sd"])
  )
}
one <- values()
times <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time(); invisible(values()); times[i] <- as.numeric(Sys.time() - t0, units = "secs")
}
write.table(one, "packages/fitdistrplus/docs/output/qqcompcens-r-values.tsv",
            sep = "\t", row.names = FALSE, quote = FALSE)
cat(sprintf("r_ms=%.9f\n", median(times) * 1000))
