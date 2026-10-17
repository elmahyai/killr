.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'aseries_n4', seed = 0, f = function() permute:::allSeries(4, 4, mirror = FALSE)),
  list(name = 'aseries_n4_mirror', seed = 0, f = function() permute:::allSeries(4, 8, mirror = TRUE)),
  list(name = 'aseries_n5', seed = 0, f = function() permute:::allSeries(5, 5, mirror = FALSE)),
  list(name = 'aseries_n6_mirror', seed = 0, f = function() permute:::allSeries(6, 12, mirror = TRUE)),
  list(name = 'aseries_allperms_mirror', seed = 0, f = function() allPerms(4, how(within = Within(type = 'series', mirror = TRUE))))
)
run_proof('allSeries-order', cases, out)
