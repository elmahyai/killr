# R-side evidence for regband(), locfit 1.5-9.12. Run from the repository root:
#   Rscript --slave packages/locfit/proof/regband-r.R
# Writes packages/locfit/docs/output/regband_r.txt. regband is not translated:
# the C band path (simul.c goldensec, rband) is not in crates/locfit.
lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
suppressPackageStartupMessages(library(locfit, lib.loc = lib))
inref <- "packages/locfit/docs/output/locfit_default_r"
x1 <- as.matrix(read.csv(file.path(inref, "in_x1.csv"), header = FALSE))
y1 <- as.vector(as.matrix(read.csv(file.path(inref, "in_y1.csv"), header = FALSE)))
msg <- function(e) if (inherits(e, "try-error")) conditionMessage(attr(e, "condition")) else "ok"
out <- character(0)
r0 <- try(regband(y1 ~ x1[, 1]), silent = TRUE)
out <- c(out, paste("default alpha:", msg(r0)))
for (a in list(c(0.7, 0.2), c(0.7, 0.05))) {
  r <- try(regband(y1 ~ x1[, 1], alpha = a), silent = TRUE)
  out <- c(out, paste0("alpha=c(", paste(a, collapse = ","), "): ", msg(r)))
  if (!inherits(r, "try-error")) {
    out <- c(out, paste(names(r), sapply(r, function(v) paste(head(round(v, 6), 5), collapse = " "))))
  }
}
writeLines(out, "packages/locfit/docs/output/regband_r.txt")
cat(out, sep = "\n")
