
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
i2 <- as.Date(c("2019-01-01", "2019-02-01", "2019-04-01", "2019-05-01"))
print(slide_period(1:4, i2, "month", identity, .before = 1))
