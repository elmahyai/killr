.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'rng_sample_10_10', seed = 42, f = function() sample.int(10, 10)),
  list(name = 'rng_runif_5', seed = 42, f = function() runif(5)),
  list(name = 'rng_sample_100_7', seed = 123, f = function() sample.int(100, 7)),
  list(name = 'rng_sample_50_50', seed = 7, f = function() sample.int(50, 50)),
  list(name = 'rng_sample_1000_50', seed = 99, f = function() sample.int(1000, 50)),
  list(name = 'rng_sample_hash_1e7', seed = 2024, f = function() sample.int(10000001, 5))
)
run_proof('rng-check', cases, out)
