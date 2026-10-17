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
s <- summary(fit, se = "nid")

E <- mk_recorder(c("plot.summary.rqs"))

record_result <- function(r) {
  E$value("ret", r[[1]])
  E$value("ylim", r[[2]])
}

cases <- list(
  all_default_ols = function() record_result(E$plot.summary.rqs(s)),
  no_ols = function() record_result(E$plot.summary.rqs(s, ols = FALSE)),
  parm_x1_ols = function() record_result(E$plot.summary.rqs(s, parm = "x1")),
  level95_ylim_ols = function() record_result(E$plot.summary.rqs(s, level = 0.95, ylim = c(-1.5, 1.5)))
)
run_cases(E, cases, file.path(out_dir, "plot.summary.rqs-r.txt"))

timed <- function() plot.summary.rqs(s)
pdf(NULL)
ms <- time_median_ms(timed)
dev.off()
writeLines(sprintf("%.17g", ms), file.path(out_dir, "plot.summary.rqs-r-time.txt"))
cat("ok plot.summary.rqs\n")
