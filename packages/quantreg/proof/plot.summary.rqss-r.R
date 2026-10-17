suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

n <- 60
i <- 1:n
x <- 2 * sin(i)
z <- cos(0.7 * i)
y <- sin(x) + 0.5 * z + 0.3 * sin(7 * i)
d <- data.frame(y = y, x = x, z = z)
f2 <- rqss(y ~ qss(x, lambda = 2) + qss(z, lambda = 1, Dorder = 0), tau = 0.5, data = d)
s <- summary(f2)

warn_text <- function() {
  tryCatch(plot.summary.rqss(s), warning = function(w) conditionMessage(w))
}

message_text <- warn_text()
cat(message_text, "\n", file = file.path(out_dir, "plot.summary.rqss-r.txt"), sep = "")

elapsed <- numeric(20)
invisible(warn_text())
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  invisible(warn_text())
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(out_dir, "plot.summary.rqss-r-time.txt"))
cat("ok plot.summary.rqss\n")
