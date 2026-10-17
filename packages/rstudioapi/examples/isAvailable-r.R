.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(rstudioapi))
stopifnot(identical(as.character(packageVersion("rstudioapi")), "0.19.0"))
rstudioapi::isAvailable()
