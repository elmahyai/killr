# R reference for gam.slist (a character vector, not a function), locfit 1.5-9.12.
# Run from the repository root:  Rscript --slave packages/locfit/proof/gam-slist-r.R
# Writes packages/locfit/docs/output/gam_slist_r.txt, one element per line.
lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")
outdir <- "packages/locfit/docs/output"
writeLines(c(is.character(gam.slist), gam.slist), file.path(outdir, "gam_slist_r.txt"))
print(gam.slist)
