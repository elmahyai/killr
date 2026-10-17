lib <- Sys.getenv("LOCFIT_RLIB", unset = "")
if (nzchar(lib)) library(locfit, lib.loc = lib) else library(locfit)
out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

cases <- list(
  "km.mrl" = function() km.mrl(c(3, 1, 2, 4), c(0, 1, 1, 0)),
  "lfgrid" = function() lfgrid(2)$mg,
  "lflim" = function() lflim(list(a = c(2, 4)), "a", c(0, 0)),
  "sjpi" = function() sjpi(seq(-1, 1, length.out = 20), c(.5, .8)),
  "spence.15" = function() spence.15(seq_len(20)),
  "spence.21" = function() spence.21(seq_len(20))
)

timed <- function(fn) {
  fn()
  samples <- numeric(20)
  for (i in seq_len(20)) {
    start <- Sys.time()
    for (j in seq_len(20)) fn()
    samples[i] <- as.numeric(difftime(Sys.time(), start, units = "secs")) *
      1000 / 20
  }
  median(samples)
}

timings <- character()
for (name in names(cases)) {
  value <- cases[[name]]()
  write.table(value, file.path(out, paste0("locfit_r_",
                                            gsub("\\.", "_", name), ".txt")),
              row.names = FALSE, col.names = FALSE, quote = FALSE)
  timings <- c(timings, paste0(name, ",r_ms=", format(timed(cases[[name]]),
                                                      digits = 17)))
}
writeLines(timings, file.path(out, "locfit_requested_r_timing.txt"))
