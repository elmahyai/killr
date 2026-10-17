.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# Write the Loblolly rows that the Python side reads (outside the timed calls).
script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
}
data_dir <- file.path(script_dir(), "data")
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
write.csv(
  data.frame(Seed = as.character(Loblolly$Seed), age = Loblolly$age,
             height = Loblolly$height),
  file.path(data_dir, "nlme-loblolly.csv"), row.names = FALSE
)

one <- function() {
  fit <- nlsList(height ~ SSasympOff(age, Asym, lrc, c0) | Seed, data = Loblolly,
                 start = c(Asym = 100, lrc = -1.5, c0 = 0))
  fm <- nlme(fit, random = Asym ~ 1)
  re <- as.matrix(ranef(fm))
  re <- re[order(rownames(re)), , drop = FALSE]
  c(fixef(fm), fm$sigma, as.numeric(logLik(fm)), as.vector(re))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
