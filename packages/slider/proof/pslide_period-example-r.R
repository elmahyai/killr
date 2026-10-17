
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slider))
i <- as.Date("2019-01-28") + 0:5
print(
  pslide_period(
    list(1:6, 7:12, i),
    i,
    "month",
    function(a, b, c) data.frame(x = a, y = b, i = c)
  )
)
