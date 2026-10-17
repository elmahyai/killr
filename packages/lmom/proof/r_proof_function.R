args <- commandArgs(trailingOnly = TRUE)
name <- args[[1]]
here <- normalizePath(file.path(getwd(), "packages", "lmom", "proof"), mustWork = FALSE)
lib <- file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3")
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
params <- list(
  lmrexp=c(1,2), lmrgam=c(2.5,1.5), lmrgev=c(0,1,.2),
  lmrglo=c(0,1,.3), lmrgno=c(0,1,.2), lmrgpa=c(0,1,.3),
  lmrgum=c(0,1), lmrkap=c(0,1,.2,.1), lmrln3=c(0,0,1),
  lmrnor=c(0,1), lmrpe3=c(0,1,.5), lmrwak=c(0,1,.5,.2,.1),
  lmrwei=c(0,1,1)
)
nmom <- if (name %in% c("lmrln3","lmrwei")) 3L else if (name %in% c("lmrgam","lmrpe3")) 4L else 5L
fn <- get(name, envir=asNamespace("lmom"))
value <- fn(params[[name]], nmom=nmom)
writeLines(sprintf("%.17g", value), file.path(here, paste0(name, "_r_values.txt")))
fn()
times <- numeric(20)
for (i in seq_len(20)) { t0 <- Sys.time(); fn(); times[i] <- as.numeric(difftime(Sys.time(), t0, units="secs")) }
writeLines(sprintf("%.17g", median(times)), file.path(here, paste0(name, "_r_time.txt")))
