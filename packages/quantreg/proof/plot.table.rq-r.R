suppressPackageStartupMessages(library(quantreg))
if (as.character(packageVersion("quantreg")) != "6.1") stop("expected quantreg 6.1")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"))

d <- as.matrix(read.table(file.path(here, "..", "quantreg", "data", "check_design.txt")))
X <- d[, 1:3]
y <- d[, 4]
df <- data.frame(y = y, x1 = X[, 2], x2 = X[, 3])
fit <- rq(y ~ x1 + x2, data = df, tau = c(0.25, 0.5, 0.75))
s <- summary(fit, se = "nid")

# plot.table.rq is the defunct table.rq message. It draws nothing, and the
# proof compares the text it prints.
text_of <- function(x) paste(capture.output(plot.table.rq(x)), collapse = "\n")

cases <- list(
  rqs_fit = function() text_of(fit),
  summary_list = function() text_of(s)
)
out <- character(0)
for (nm in names(cases)) {
  out <- c(out, paste("CASE", nm), cases[[nm]]())
}
writeLines(out, file.path(out_dir, "plot.table.rq-r.txt"))

timed <- function() text_of(fit)
ms <- {
  timed()
  el <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    timed()
    el[[i]] <- as.numeric(Sys.time()) - t0
  }
  median(el) * 1000
}
writeLines(sprintf("%.17g", ms), file.path(out_dir, "plot.table.rq-r-time.txt"))
cat("ok plot.table.rq\n")
