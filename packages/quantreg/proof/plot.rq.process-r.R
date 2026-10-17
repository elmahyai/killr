suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

d <- as.matrix(read.table(file.path(here, "..", "quantreg", "data", "check_design.txt")))
X <- d[, 1:3]
y <- d[, 4]
df <- data.frame(y = y, x1 = X[, 2], x2 = X[, 3])
fit <- rq(y ~ x1 + x2, tau = -1, data = df)

E <- mk_recorder(c("plot.rq.process"))

cases <- list(
  default_3x2 = function() E$plot.rq.process(fit),
  layout_2x2 = function() E$plot.rq.process(fit, nrow = 2, ncol = 2)
)
run_cases(E, cases, file.path(out_dir, "plot.rq.process-r.txt"))

timed <- function() plot.rq.process(fit)
pdf(NULL)
ms <- time_median_ms(timed)
dev.off()
writeLines(sprintf("%.17g", ms), file.path(out_dir, "plot.rq.process-r-time.txt"))
cat("ok plot.rq.process\n")
