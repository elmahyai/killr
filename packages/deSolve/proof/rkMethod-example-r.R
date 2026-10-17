.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
print(rkMethod())
print(rkMethod("rk45dp7"))
