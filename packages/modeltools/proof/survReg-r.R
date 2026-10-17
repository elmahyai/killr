.libPaths(c(path.expand("~/R/library"), "/tmp/modeltools-Rlib", .libPaths()))
suppressPackageStartupMessages(library(modeltools))
suppressPackageStartupMessages(library(survival))

n <- 80
i <- seq_len(n)
time <- 0.4 + ((i * 19) %% 31) / 10
status <- ifelse(i %% 4 == 0, 0, 1)
x <- ((i * 7) %% 13) / 5 - 1
wt <- 1 + (i %% 3) / 2
df <- data.frame(time = time, status = status, x = x)
mf <- dpp(survReg, Surv(time, status) ~ x, data = df)
fit <- fit(survReg, mf, weights = wt, dist = "extreme")
cat(paste(format(c(fit$coefficients, fit$scale, fit$loglik[[2]]),
                  digits = 17), collapse = "\n"), "\n", sep = "")
elapsed <- numeric(20)
for (j in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    fit(survReg, mf, weights = wt, dist = "extreme")
    elapsed[[j]] <- as.numeric(Sys.time()) - t0
}
cat("MS\n", sprintf("%.17g\n", median(elapsed) * 1000), sep = "")
