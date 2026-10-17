.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
events <- sort(c(0, 2, 3, 4 + 1e-10, 5, 7 - 1e-10,
                 7 + 6e-15, 7.5, 9, 24.9999, 25, 80, 1001, 1e300))
times <- sort(c(0, 1:7, 4.5, 6.75, 7.5, 9.2, 9.0001, 25, 879, 1e3, 1e300 + 5))
nearest <- nearestEvent(times, events)
print(data.frame(times = times, nearest = nearest))
