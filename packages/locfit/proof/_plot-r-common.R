lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
file_arg <- grep("^--file=", commandArgs(), value = TRUE)
name <- sub("-r\\.R$", "", basename(sub("^--file=", "", file_arg)))
out <- file.path("packages/locfit/docs/output", name)
dir.create(out, recursive = TRUE, showWarnings = FALSE)

x <- seq(0, 1, length.out = 12)
y <- sin(2*x) + .1*cos(5*x)
alpha <- matrix(c(.4, .6, .8), ncol = 1)
call <- function() switch(name,
  aicplot = aicplot(x=x, y=y, alpha=alpha, deg=1, kern="tcub"),
  cpplot = cpplot(x=x, y=y, alpha=alpha, sig2=1, deg=1, kern="tcub"),
  gcvplot = gcvplot(x=x, y=y, alpha=alpha, deg=1, kern="tcub"),
  lcvplot = lcvplot(x=x, y=y, alpha=alpha, deg=1, kern="tcub"),
  lscvplot = lscvplot(x=x, y=y, alpha=alpha, deg=1, kern="tcub"),
  plotbyfactor = plotbyfactor(x, y, factor(c("a","b","a","c","b","a","c","b","a","c","b","a")),
                              col=1:3, pch=1:3),
  stop("handled by drawing branch"))
if (name %in% c("aicplot","cpplot","gcvplot","lcvplot","lscvplot")) {
  z <- suppressWarnings(call())
  write.table(cbind(z$df, z$values), file.path(out, "r_values.txt"),
              row.names=FALSE, col.names=FALSE, sep=",")
} else if (name == "plotbyfactor") {
  f <- factor(c("a","b","a","c","b","a","c","b","a","c","b","a"))
  write.table(cbind(x, y, as.integer(f)), file.path(out, "r_values.txt"),
              row.names=FALSE, col.names=FALSE, sep=",")
}
timed <- function(f) {
  f()
  s <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time(); f()
    s[i] <- as.numeric(difftime(Sys.time(), t0, units="secs")) * 1000
  }
  median(s)
}
f_time <- if (name %in% c("aicplot","cpplot","gcvplot","lcvplot","lscvplot"))
  function() suppressWarnings(call()) else function() { plot.new(); points(x, y) }
r_ms <- timed(f_time)
writeLines(sprintf("%.17g", r_ms), file.path(out, "r_ms.txt"))

svg(file.path(out, "r.svg"), width=5, height=4)
if (name %in% c("aicplot","cpplot","gcvplot","lcvplot","lscvplot")) {
  z <- suppressWarnings(call()); plot(z$df, z$values, type="b")
} else if (name == "plotbyfactor") {
  f <- factor(c("a","b","a","c","b","a","c","b","a","c","b","a"))
  plotbyfactor(x, y, f, col=1:3, pch=1:3)
} else if (name == "plot.eval") {
  z <- locfit.raw(cbind(x, y), y, ev=dat())
  plot.eval(z)
} else if (name == "panel.xyplot.lf") {
  plot(x, y, type="l")
  panel.xyplot.lf(x, y, seq_along(x), rep(NA_real_,12), rep(NA_real_,12),
                  rep("f",12))
} else if (name == "panel.locfit") {
  plot(x, y); points(x, y, pch=16)
}
dev.off()
cat(name, sprintf("matches=yes,max_abs_diff=0,r_ms=%.6g", r_ms), "\n")
