suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

d <- as.matrix(read.table(file.path(here, "..", "quantreg", "data", "check_design.txt")))
X <- d[, 1:3]
y <- d[, 4]
df <- data.frame(y = y, x1 = X[, 2], x2 = X[, 3])
fit <- rq(y ~ x1 + x2, data = df, tau = c(0.25, 0.5, 0.75))

E <- mk_recorder(c("plot.rqs"))

cases <- list(
  all_default_ols = function() E$value("ret", E$plot.rqs(fit)),
  no_ols = function() E$value("ret", E$plot.rqs(fit, ols = FALSE)),
  parm_x1_ols = function() E$value("ret", E$plot.rqs(fit, parm = "x1")),
  fixed_ylim_ols = function() E$value("ret", E$plot.rqs(fit, ylim = c(-1.5, 1.5)))
)
run_cases(E, cases, file.path(out_dir, "plot.rqs-r.txt"))

timed <- function() plot.rqs(fit)
pdf(NULL)
ms <- time_median_ms(timed)
dev.off()
writeLines(sprintf("%.17g", ms), file.path(out_dir, "plot.rqs-r-time.txt"))
cat("ok plot.rqs\n")
