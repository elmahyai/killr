.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'ff_full10', seed = 42, f = function() shuffleFree(10, 10)),
  list(name = 'ff_part10_3', seed = 1, f = function() shuffleFree(10, 3)),
  list(name = 'ff_vec', seed = 7, f = function() shuffleFree(c(10, 20, 30, 40, 50), 5)),
  list(name = 'ff_one', seed = 3, f = function() shuffleFree(1, 1)),
  list(name = 'ff_large_k', seed = 99, f = function() shuffleFree(1000, 50)),
  list(name = 'ff_pair', seed = 11, f = function() shuffleFree(c(2, 4, 6, 8), 2)),
  list(name = 'ff_hash', seed = 2024, f = function() shuffleFree(10000001, 5)),
  list(name = 'ff_zero', seed = 5, f = function() shuffleFree(5, 0))
)
run_proof('shuffleFree', cases, out)
