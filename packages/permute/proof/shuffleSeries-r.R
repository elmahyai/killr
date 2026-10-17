.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'ss_plain', seed = 5, f = function() shuffleSeries(1:6)),
  list(name = 'ss_mirror', seed = 6, f = function() shuffleSeries(1:6, mirror = TRUE)),
  list(name = 'ss_mirror_vals', seed = 8, f = function() shuffleSeries(c(10, 20, 30, 40, 50), mirror = TRUE)),
  list(name = 'ss_start', seed = 9, f = function() shuffleSeries(1:7, start = 3)),
  list(name = 'ss_start_mirror', seed = 10, f = function() shuffleSeries(1:7, mirror = TRUE, start = 2)),
  list(name = 'ss_flip_true', seed = 11, f = function() shuffleSeries(1:6, mirror = TRUE, start = 4, flip = TRUE)),
  list(name = 'ss_flip_false', seed = 12, f = function() shuffleSeries(1:6, mirror = TRUE, start = 1, flip = FALSE)),
  list(name = 'ss_start_big', seed = 13, f = function() shuffleSeries(1:10, start = 12))
)
run_proof('shuffleSeries', cases, out)
