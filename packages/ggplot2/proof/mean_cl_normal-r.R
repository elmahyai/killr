lib <- tempfile("hmisc-lib-")
dir.create(lib)
src <- tempfile("Hmisc-")
dir.create(file.path(src, "R"), recursive = TRUE)
writeLines(c(
  "Package: Hmisc",
  "Version: 5.3-0",
  "Title: Harrell Miscellaneous",
  "Description: Exports smean.cl.normal as published in Hmisc 5.3-0.",
  "License: GPL (>= 2)",
  "Imports: stats"
), file.path(src, "DESCRIPTION"))
writeLines("export(smean.cl.normal)", file.path(src, "NAMESPACE"))
writeLines(c(
  "smean.cl.normal <- function(x, mult=qt((1+conf.int)/2,n-1),",
  "                            conf.int=.95, na.rm=TRUE)",
  "{",
  "  if(na.rm) x <- x[!is.na(x)]",
  "  n <- length(x)",
  "  if(n < 2)",
  "    return(c(Mean=mean(x),Lower=NA,Upper=NA))",
  "  ",
  "  xbar <- sum(x)/n",
  "  se <- sqrt(sum((x - xbar)^2) / n / (n-1))",
  "  c(Mean=xbar, Lower=xbar - mult*se, Upper=xbar + mult*se)",
  "}",
  ""
), file.path(src, "R", "smean.R"))
invisible(utils::capture.output(install.packages(src, repos = NULL, lib = lib, quiet = TRUE, type = "source")))
if (!dir.exists(file.path(lib, "Hmisc"))) stop("Hmisc install failed")
.libPaths(c(lib, .libPaths()))
suppressPackageStartupMessages(library(ggplot2))
if (packageDescription("ggplot2")$Version != "4.0.3") stop("expected ggplot2 4.0.3")
options(warn = -1)
set.seed(1)
x <- rnorm(100)
one <- function() {
mean_cl_normal(x)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
nums <- as.numeric(unlist(value, use.names = FALSE))
cat(jsonlite::toJSON(list(value = nums, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
