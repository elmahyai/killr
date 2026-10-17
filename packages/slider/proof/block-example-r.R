
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
x <- 1:6
i <- as.Date("2019-01-01") + c(-2:2, 31)
print(block(i, i, period = "year"))
